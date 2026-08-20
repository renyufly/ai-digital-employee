"""Readable, framework-free Tool Calling loop for the digital employee."""

from __future__ import annotations

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
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse: ...


ToolDispatcher = Callable[[str, object], Awaitable[ToolResult]]


class AgentService:
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

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ]
        traces: list[AgentTrace] = []
        sources: dict[tuple[str, int | None, str], Source] = {}
        executed_calls: set[str] = set()

        for step in range(1, self.settings.max_agent_steps + 1):
            started = perf_counter()
            logger.info("Agent LLM round started round=%d", step)
            try:
                response = await self.llm_client.complete(messages, self.schemas)
            except LLMRequestError as exc:
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
                answer = (response.content or "").strip()
                if not answer:
                    return self._error_result(
                        step, "LLM_EMPTY_ANSWER", "模型未返回有效答案", traces, sources
                    )
                return AgentResult(answer=answer, traces=traces, sources=list(sources.values()))

            messages.append(self._assistant_tool_message(response))
            for call in response.tool_calls:
                parsed_arguments, parse_error = self._parse_arguments(call.arguments)
                signature = self._call_signature(call.name, parsed_arguments, call.arguments)
                if signature in executed_calls:
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
                    result = ToolResult(
                        success=False,
                        error_code="INVALID_ARGUMENT",
                        message=f"工具 {call.name} 的参数不是有效 JSON 对象",
                    )
                else:
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
                for source in result.sources:
                    sources[(source.file, source.page, source.chunk_id)] = source
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
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}, True
        if not isinstance(parsed, dict):
            return parsed, True
        return parsed, False

    @staticmethod
    def _call_signature(name: str, arguments: object, raw: str) -> str:
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
        safe_traces = list(traces)
        safe_traces.append(AgentTrace(step=step, type="error", summary=message))
        return AgentResult(
            answer=message,
            traces=safe_traces,
            sources=list((sources or {}).values()),
            error_code=code,
        )
