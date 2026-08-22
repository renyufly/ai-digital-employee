'''
AgentService 的单元测试，核心目的是：不用真实 LLM、RAG、ERP，
就验证 Agent Loop 在各种情况下是否按预期工作
'''
from collections import deque
from typing import Any

import pytest

from app.agent.schemas import Source, ToolResult
from app.agent.service import AgentService
from app.core.config import Settings
from app.core.errors import LLMRequestError
from app.llm.client import LLMResponse, LLMToolCall


def make_settings(**overrides: Any) -> Settings:
    '''
    生成测试专用配置，例如模型名、最大 Agent 步数。
    overrides 可以临时覆盖，比如测试最大步数时改成 2
    '''
    values = {
        "openrouter_api_key": "test-key",
        "llm_model": "openai/gpt-oss-20b:free",
        "max_agent_steps": 5,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


class FakeLLM:
    '''
    假的 LLM。它不会真的访问 OpenRouter
    '''
    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = deque(responses)
        self.requests: list[list[dict[str, Any]]] = []

    async def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> LLMResponse:
        self.requests.append([dict(message) for message in messages])
        return self.responses.popleft()


def tool_call(call_id: str, name: str, arguments: str) -> LLMResponse:
    '''
    快速模拟模型返回 Tool Call
    '''
    return LLMResponse(
        content=None,
        tool_calls=[LLMToolCall(id=call_id, name=name, arguments=arguments)],
        model="fake/model",
    )


@pytest.mark.asyncio
async def test_agent_returns_direct_answer_without_tool() -> None:
    '''
    测试：不调用工具，直接回答
    '''
    fake = FakeLLM([LLMResponse(content="你好，我可以帮你查询。")])
    called = False

    async def dispatcher(name: str, arguments: object) -> ToolResult:
        nonlocal called
        called = True
        return ToolResult(success=True, message="unused")

    result = await AgentService(fake, settings=make_settings(), dispatcher=dispatcher).run("你好")

    assert result.answer == "你好，我可以帮你查询。"
    assert result.error_code is None
    assert not called


@pytest.mark.asyncio
async def test_agent_executes_single_tool_and_preserves_protocol_messages() -> None:
    '''
    单工具调用
    '''
    fake = FakeLLM(
        [
            tool_call("call-1", "query_order", '{"order_no":"10001"}'),
            LLMResponse(content="订单 10001 已发货。"),
        ]
    )
    received: list[tuple[str, object]] = []

    async def dispatcher(name: str, arguments: object) -> ToolResult:
        received.append((name, arguments))
        return ToolResult(success=True, data={"status": "已发货"}, message="查询成功")

    result = await AgentService(fake, settings=make_settings(), dispatcher=dispatcher).run(
        "查询订单 10001"
    )

    assert result.answer == "订单 10001 已发货。"
    assert received == [("query_order", {"order_no": "10001"})]
    second_request = fake.requests[1]
    assert second_request[-2]["role"] == "assistant"
    assert second_request[-2]["tool_calls"][0]["id"] == "call-1"
    assert second_request[-1]["role"] == "tool"
    assert second_request[-1]["tool_call_id"] == "call-1"


@pytest.mark.asyncio
async def test_agent_executes_conditional_multi_tool_and_deduplicates_sources() -> None:
    '''
    多工具调用 + 来源去重
    '''
    source = Source(
        file="refund_policy.pdf",
        page=1,
        chunk_id="refund_policy-p1-c1",
        content="已发货订单需要先完成退货。",
        score=0.8,
    )
    fake = FakeLLM(
        [
            tool_call("call-1", "query_order", '{"order_no":"10001"}'),
            tool_call("call-2", "search_company_docs", '{"query":"已发货订单退款政策"}'),
            LLMResponse(content="订单已发货，需先退货，验收后进入退款流程。"),
        ]
    )

    async def dispatcher(name: str, arguments: object) -> ToolResult:
        if name == "query_order":
            return ToolResult(success=True, data={"status": "已发货"}, message="查询成功")
        return ToolResult(success=True, data={"context": source.content}, message="检索成功", sources=[source, source])

    result = await AgentService(fake, settings=make_settings(), dispatcher=dispatcher).run("综合问题")

    assert result.error_code is None
    assert [trace.name for trace in result.traces if trace.type == "tool_start"] == [
        "query_order",
        "search_company_docs",
    ]
    assert result.sources == [source]


@pytest.mark.asyncio
async def test_invalid_tool_json_is_returned_to_model_as_tool_error() -> None:
    '''
    模型返回非法 JSON
    '''
    fake = FakeLLM(
        [
            tool_call("bad-1", "calculate", "not-json"),
            LLMResponse(content="计算参数无效，无法完成计算。"),
        ]
    )
    called = False

    async def dispatcher(name: str, arguments: object) -> ToolResult:
        nonlocal called
        called = True
        return ToolResult(success=True, message="unused")

    result = await AgentService(fake, settings=make_settings(), dispatcher=dispatcher).run("计算")

    assert not called
    assert result.error_code is None
    assert "INVALID_ARGUMENT" in fake.requests[1][-1]["content"]


@pytest.mark.asyncio
async def test_repeated_tool_call_stops_loop() -> None:
    '''
    防止重复 Tool Call 死循环
    '''
    fake = FakeLLM(
        [
            tool_call("call-1", "query_order", '{"order_no":"10001"}'),
            tool_call("call-2", "query_order", '{ "order_no": "10001" }'),
        ]
    )

    async def dispatcher(name: str, arguments: object) -> ToolResult:
        return ToolResult(success=False, error_code="ERP_LOGIN_FAILED", message="登录失败")

    result = await AgentService(fake, settings=make_settings(), dispatcher=dispatcher).run("查订单")

    assert result.error_code == "REPEATED_TOOL_CALL"
    assert "重复工具调用" in result.answer


@pytest.mark.asyncio
async def test_max_agent_steps_returns_understandable_error() -> None:
    '''
    最大 Agent 步数
    '''
    fake = FakeLLM(
        [
            tool_call("call-1", "calculate", '{"expression":"1+1"}'),
            tool_call("call-2", "calculate", '{"expression":"2+2"}'),
        ]
    )

    async def dispatcher(name: str, arguments: object) -> ToolResult:
        return ToolResult(success=True, data={"result": 2}, message="计算成功")

    result = await AgentService(
        fake, settings=make_settings(max_agent_steps=2), dispatcher=dispatcher
    ).run("持续计算")

    assert result.error_code == "MAX_AGENT_STEPS_EXCEEDED"
    assert "最大执行轮数 2" in result.answer


@pytest.mark.asyncio
async def test_unknown_tool_is_safely_dispatched_and_model_can_explain() -> None:
    '''
    未知工具
    '''
    fake = FakeLLM(
        [
            tool_call("call-1", "delete_database", "{}"),
            LLMResponse(content="该工具不可用，我无法执行。"),
        ]
    )

    async def dispatcher(name: str, arguments: object) -> ToolResult:
        return ToolResult(success=False, error_code="UNKNOWN_TOOL", message="未知工具")

    result = await AgentService(fake, settings=make_settings(), dispatcher=dispatcher).run("危险操作")

    assert result.error_code is None
    assert "UNKNOWN_TOOL" in fake.requests[1][-1]["content"]
    assert any(trace.type == "error" and trace.name == "delete_database" for trace in result.traces)


@pytest.mark.asyncio
async def test_empty_final_answer_returns_explicit_error() -> None:
    '''
    最终答案为空
    '''
    result = await AgentService(
        FakeLLM([LLMResponse(content="   ")]), settings=make_settings()
    ).run("你好")

    assert result.error_code == "LLM_EMPTY_ANSWER"
    assert "未返回有效答案" in result.answer


@pytest.mark.asyncio
async def test_llm_request_error_becomes_agent_error_result() -> None:
    '''
    LLM 本身请求失败
    '''
    class FailingLLM:
        async def complete(
            self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
        ) -> LLMResponse:
            raise LLMRequestError("LLM_AUTH_FAILED", "OpenRouter API Key 无效或无权限")

    result = await AgentService(FailingLLM(), settings=make_settings()).run("你好")

    assert result.error_code == "LLM_AUTH_FAILED"
    assert result.answer == "OpenRouter API Key 无效或无权限"
