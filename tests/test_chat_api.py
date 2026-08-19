from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio

from app.agent.schemas import AgentResult, AgentTrace, Source
from app.api.chat import get_agent_service
from app.core.errors import LLMConfigurationError
from app.main import app


class FakeAgentService:
    def __init__(self, results: list[AgentResult]) -> None:
        self.results = iter(results)
        self.messages: list[str] = []

    async def run(self, user_message: str) -> AgentResult:
        self.messages.append(user_message)
        return next(self.results)


@pytest_asyncio.fixture
async def api_client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_chat_serializes_agent_result_and_request_id(api_client: httpx.AsyncClient) -> None:
    source = Source(
        file="refund_policy.pdf",
        page=1,
        chunk_id="refund_policy-p1-c1",
        content="退款将在审核通过后原路退回。",
        score=0.81,
    )
    fake = FakeAgentService(
        [
            AgentResult(
                answer="退款通常会在审核通过后的指定时限内到账。",
                traces=[
                    AgentTrace(
                        step=1,
                        type="tool_result",
                        name="search_company_docs",
                        summary="执行成功",
                        duration_ms=12,
                    )
                ],
                sources=[source],
            )
        ]
    )
    app.dependency_overrides[get_agent_service] = lambda: fake

    response = await api_client.post("/api/chat", json={"message": "  退款多久到账？  "})

    assert response.status_code == 200
    body = response.json()
    assert fake.messages == ["退款多久到账？"]
    assert body["answer"].startswith("退款通常")
    assert body["traces"][0]["name"] == "search_company_docs"
    assert body["sources"][0]["chunk_id"] == "refund_policy-p1-c1"
    assert body["audio_url"] is None
    assert body["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_each_chat_request_is_independent(api_client: httpx.AsyncClient) -> None:
    fake = FakeAgentService(
        [AgentResult(answer="第一条"), AgentResult(answer="第二条")]
    )
    app.dependency_overrides[get_agent_service] = lambda: fake

    first = await api_client.post(
        "/api/chat", json={"message": "问题一", "session_id": "same-session"}
    )
    second = await api_client.post(
        "/api/chat", json={"message": "问题二", "session_id": "same-session"}
    )

    assert fake.messages == ["问题一", "问题二"]
    assert first.json()["request_id"] != second.json()["request_id"]
    assert first.json()["answer"] == "第一条"
    assert second.json()["answer"] == "第二条"


@pytest.mark.asyncio
async def test_three_core_questions_share_one_response_contract(
    api_client: httpx.AsyncClient,
) -> None:
    questions = [
        "退款多久到账？",
        "帮我查询订单 10001。",
        (
            "查询订单 10001，如果已经发货，告诉我物流信息，"
            "同时根据公司的退款政策告诉我是否还能申请退款。"
        ),
    ]
    fake = FakeAgentService([AgentResult(answer=f"回答 {index}") for index in range(3)])
    app.dependency_overrides[get_agent_service] = lambda: fake

    responses = [
        await api_client.post("/api/chat", json={"message": question})
        for question in questions
    ]

    expected_keys = {"answer", "traces", "sources", "audio_url", "request_id"}
    assert fake.messages == questions
    assert all(response.status_code == 200 for response in responses)
    assert all(set(response.json()) == expected_keys for response in responses)


@pytest.mark.asyncio
@pytest.mark.parametrize("message", ["", "   ", "x" * 2_001])
async def test_chat_rejects_empty_or_overlong_messages(
    api_client: httpx.AsyncClient, message: str
) -> None:
    response = await api_client.post("/api/chat", json={"message": message})

    assert response.status_code == 422
    assert set(response.json()) == {
        "answer",
        "traces",
        "sources",
        "audio_url",
        "request_id",
    }
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_chat_rejects_invalid_session_id_and_unknown_fields(
    api_client: httpx.AsyncClient,
) -> None:
    responses = [
        await api_client.post(
            "/api/chat", json={"message": "你好", "session_id": "   "}
        ),
        await api_client.post(
            "/api/chat", json={"message": "你好", "history": ["不应接受"]}
        ),
    ]

    assert all(response.status_code == 422 for response in responses)


@pytest.mark.asyncio
async def test_expected_agent_error_keeps_chat_response_contract(
    api_client: httpx.AsyncClient,
) -> None:
    fake = FakeAgentService(
        [
            AgentResult(
                answer="OpenRouter 请求超时",
                traces=[AgentTrace(step=1, type="error", summary="OpenRouter 请求超时")],
                error_code="LLM_TIMEOUT",
            )
        ]
    )
    app.dependency_overrides[get_agent_service] = lambda: fake

    response = await api_client.post("/api/chat", json={"message": "查询订单 10001"})

    assert response.status_code == 504
    assert response.json()["answer"] == "OpenRouter 请求超时"
    assert response.json()["traces"][0]["type"] == "error"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_missing_llm_configuration_is_clear_and_structured(
    api_client: httpx.AsyncClient,
) -> None:
    def unavailable_service() -> None:
        raise LLMConfigurationError("缺少 OPENROUTER_API_KEY，请在项目根目录 .env 中填写")

    app.dependency_overrides[get_agent_service] = unavailable_service

    response = await api_client.post("/api/chat", json={"message": "你好"})

    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["answer"]
    assert response.json()["traces"][0]["type"] == "error"


@pytest.mark.asyncio
async def test_unknown_exception_is_logged_but_not_exposed(api_client: httpx.AsyncClient) -> None:
    class BrokenAgent:
        async def run(self, user_message: str) -> AgentResult:
            raise RuntimeError("secret internal detail")

    app.dependency_overrides[get_agent_service] = BrokenAgent

    response = await api_client.post("/api/chat", json={"message": "你好"})

    assert response.status_code == 500
    assert response.json()["answer"] == "服务发生未预期错误，请稍后重试"
    assert "secret internal detail" not in response.text


def test_openapi_includes_three_core_chat_examples() -> None:
    schema = app.openapi()
    examples = schema["components"]["schemas"]["ChatRequest"]["examples"]

    assert len(examples) == 3
    assert any("退款" in example["message"] for example in examples)
    assert any("订单 10001" in example["message"] for example in examples)
    assert any("同时" in example["message"] for example in examples)


@pytest.mark.asyncio
async def test_api_docs_are_available(api_client: httpx.AsyncClient) -> None:
    docs_response = await api_client.get("/docs")
    schema_response = await api_client.get("/openapi.json")

    assert docs_response.status_code == 200
    assert schema_response.status_code == 200
    assert "/api/chat" in schema_response.json()["paths"]
