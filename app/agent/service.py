"""Readable, framework-free Tool Calling loop for the digital employee."""
'''Agent 的核心调度器:
不断让 LLM 决定下一步 → 执行它选择的 Tool → 把 Tool 结果交回 LLM → 直到 LLM 给出最终答案
'''

'''
没有使用 LangChain，而是自己实现了一个最小 Tool Calling Agent Loop。每一轮把完整 messages 和三个白名单 Tool Schema 发给模型，如果模型直接生成文本就结束；
如果模型返回 Tool Call，就先把 assistant 的 Tool Call 消息加入上下文，再解析 JSON 参数，通过 Registry 做白名单和 Pydantic 二次校验后执行真实工具，
之后利用对应的 tool_call_id 把 ToolResult 返回给模型。循环过程中我会累计 Trace 和 RAG Source，同时使用最大 5 步和规范化 Tool 参数后的重复调用检测防止死循环。
这样 LLM 只负责“决定调用什么”，真正执行、权限和错误边界都由 Python 控制.
'''

from __future__ import annotations   # 让类型注解延迟解析

from collections.abc import Awaitable, Callable
import json
import logging
from time import perf_counter
from typing import Any, Protocol

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.schemas import AgentResult, AgentTrace, Source, ToolResult
from app.agent.tool_registry import dispatch_tool, tool_schemas
from app.core.config import Settings, get_settings
from app.core.errors import LLMRequestError
from app.llm.client import LLMClient, LLMResponse


logger = logging.getLogger(__name__)


class LLMGateway(Protocol):
    '''
    规定：
    只要某个对象有这样一个 complete() 方法，就认为它是可以使用的 LLM.
    方便真实LLMClient 与 测试用FakeLLM  "dependency injection"
    '''
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse: ...


ToolDispatcher = Callable[[str, object], Awaitable[ToolResult]]


class AgentService:
    '''整个 Agent Loop'''
    def __init__(
        self,
        llm_client: LLMGateway | None = None,
        *,
        settings: Settings | None = None,
        dispatcher: ToolDispatcher = dispatch_tool,
        schemas: list[dict[str, Any]] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm_client = llm_client or LLMClient(self.settings)
        self.dispatcher = dispatcher
        self.schemas = schemas if schemas is not None else tool_schemas()

    async def run(self, user_message: str) -> AgentResult:
        message = user_message.strip()
        if not message:
            return self._error_result(0, "INVALID_ARGUMENT", "问题不能为空", [])

        '''
        创建初始发送给LLM的消息 (包含SystemPrompt与用户消息)
        '''
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ] 
        traces: list[AgentTrace] = [] # 用于Streamlit 里的“可解释执行轨迹”

        '''
        用字典保存 RAG 来源. dict会去重. 
        key: (source.file, source.page, source.chunk_id)
        '''
        sources: dict[tuple[str, int | None, str], Source] = {}

        '''
        防 Agent 死循环: 如果连续两次Tool call同样参数，就是重复调用
        '''
        executed_calls: set[str] = set()

        for step in range(1, self.settings.max_agent_steps + 1):
            '''
            Agent核心循环. 若max_agent_steps=5，就是模型最多决策5轮.
            防止无限消耗token.
            '''
            started = perf_counter() # perf性能开始计时
            logger.info("Agent LLM round started round=%d", step)

            try:
                '''
                真正向 OpenRouter 发请求. (不用考虑具体LLM型号)
                '''
                response = await self.llm_client.complete(messages, self.schemas)
            except LLMRequestError as exc:
                '''
                失败请求也统一封装为 AgentResult
                '''
                logger.warning(
                    "Agent LLM round failed round=%d duration_ms=%d error_code=%s",
                    step,
                    round((perf_counter() - started) * 1000),
                    exc.code,
                )
                return self._error_result(step, exc.code, exc.message, traces, sources)

            llm_duration_ms = round((perf_counter() - started) * 1000)
            logger.info(
                "Agent LLM round completed round=%d duration_ms=%d tool_calls=%d",
                step,
                llm_duration_ms,
                len(response.tool_calls),
            )

            '''
            可解释Agent：模型做了什么  (不是Chain of Thought,未展示推理过程)
            '''
            traces.append(
                AgentTrace(
                    step=step,
                    type="agent",
                    summary=(
                        f"模型选择了 {len(response.tool_calls)} 个工具"
                        if response.tool_calls
                        else "模型生成最终回答"
                    ),
                    duration_ms=llm_duration_ms,
                )
            )

            if not response.tool_calls:
                '''
                最简单回复情况-模型未Tool call
                '''
                answer = (response.content or "").strip()
                if not answer:
                    return self._error_result(
                        step, "LLM_EMPTY_ANSWER", "模型未返回有效答案", traces, sources
                    )
                return AgentResult(answer=answer, traces=traces, sources=list(sources.values()))

            '''
            模型Tool call：要把 assistant Tool Call 放回 messages.
            让模型知道这个 result 对应哪个调用
            '''
            messages.append(self._assistant_tool_message(response))
            for call in response.tool_calls:
                '''
                逐个执行 Tool Call
                '''
                parsed_arguments, parse_error = self._parse_arguments(call.arguments)
                signature = self._call_signature(call.name, parsed_arguments, call.arguments) # 生成 Tool Call 唯一签名
                if signature in executed_calls:
                    ''' 检测唯一签名来防止重复 Tool Call '''
                    return self._error_result(
                        step,
                        "REPEATED_TOOL_CALL",
                        f"检测到重复工具调用 {call.name}，已停止以避免死循环",
                        traces,
                        sources,
                    )
                executed_calls.add(signature)

                traces.append(
                    AgentTrace(step=step, type="tool_start", name=call.name, summary=f"开始执行 {call.name}")
                )
                logger.info("Agent tool started round=%d tool=%s", step, call.name)

                tool_started = perf_counter()
                if parse_error:
                    '''
                    JSON 解析验证模型输出,因为Tool schema 只能“指导”模型的输出格式
                    '''
                    result = ToolResult(
                        success=False,
                        error_code="INVALID_ARGUMENT",
                        message=f"工具 {call.name} 的参数不是有效 JSON 对象",
                    )
                else:
                    ''' 真正调用 Tool : Agent 与 Tool 解耦 (Agent 不知道 Tool 内部到底怎么实现)'''
                    result = await self.dispatcher(call.name, parsed_arguments)

                duration_ms = round((perf_counter() - tool_started) * 1000)
                logger.info(
                    "Agent tool completed round=%d tool=%s success=%s duration_ms=%d error_code=%s",
                    step,
                    call.name,
                    result.success,
                    duration_ms,
                    result.error_code or "-",
                )
                traces.append(
                    AgentTrace(
                        step=step,
                        type="tool_result" if result.success else "error",
                        name=call.name,
                        summary=("执行成功" if result.success else f"执行失败：{result.error_code}"),
                        duration_ms=duration_ms,
                    )
                )

                ''' 收集 RAG 来源 '''
                for source in result.sources:
                    sources[(source.file, source.page, source.chunk_id)] = source

                ''' 把 Tool Result 返回给 LLM. 然后进入下一轮'''
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result.model_dump_json(),
                    }
                )

        logger.warning(
            "Agent stopped at maximum rounds max_rounds=%d", self.settings.max_agent_steps
        )
        return self._error_result(
            self.settings.max_agent_steps,
            "MAX_AGENT_STEPS_EXCEEDED",
            f"Agent 已达到最大执行轮数 {self.settings.max_agent_steps}，请缩小问题范围后重试",
            traces,
            sources,
        )

    @staticmethod
    def _assistant_tool_message(response: LLMResponse) -> dict[str, Any]:
        ''' 
        把内部统一的LLMResponse 重新变回 OpenAI Tool Calling 消息格式
        Agent Loop 中非常关键的“协议转换层”
        '''
        return {
            "role": "assistant",
            "content": response.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments},
                }
                for call in response.tool_calls
            ],
        }

    @staticmethod
    def _parse_arguments(raw: str) -> tuple[object, bool]:
        ''' 
        解析如raw = '{"order_no":"10001"}' 
        '''
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}, True
        if not isinstance(parsed, dict):
            return parsed, True
        return parsed, False

    @staticmethod
    def _call_signature(name: str, arguments: object, raw: str) -> str:
        '''
        生成 Tool Call 唯一签名. 判断两个 Tool Call 是否实际上相同
        normalize 参数是因为模型可能输出文本不一样，但含义完全一样. 
        '''
        try:
            normalized = json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError):
            normalized = raw
        return f"{name}:{normalized}"

    @staticmethod
    def _error_result(
        step: int,
        code: str,
        message: str,
        traces: list[AgentTrace],
        sources: dict[tuple[str, int | None, str], Source] | None = None,
    ) -> AgentResult:
        '''
        把所有 Agent 错误统一转换成 AgentResult.
        错误本身也是一个合法 Agent 响应, API 层不用面对几十种 Exception.
        '''
        safe_traces = list(traces)
        safe_traces.append(AgentTrace(step=step, type="error", summary=message))
        return AgentResult(
            answer=message,
            traces=safe_traces,
            sources=list((sources or {}).values()),
            error_code=code,
        )
