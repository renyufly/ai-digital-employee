from __future__ import annotations

import httpx
import pytest

from frontend.client import ChatApiClient, FrontendServiceError


def test_frontend_client_calls_health_and_chat_over_http() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(
            200,
            json={
                "answer": "订单 10001 已发货。",
                "traces": [
                    {
                        "step": 1,
                        "type": "tool_result",
                        "name": "query_order",
                        "summary": "执行成功",
                        "duration_ms": 20,
                    }
                ],
                "sources": [],
                "audio_url": None,
                "request_id": "request-1",
            },
        )

    client = ChatApiClient(transport=httpx.MockTransport(handler))

    assert client.health() is True
    result = client.ask("帮我查询订单 10001。", session_id="ui-session")

    assert result.success is True
    assert result.payload.answer == "订单 10001 已发货。"
    assert result.payload.traces[0].name == "query_order"
    assert requests[1].url.path == "/api/chat"
    assert b'"session_id":"ui-session"' in requests[1].content


def test_frontend_client_preserves_structured_backend_errors() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            503,
            json={
                "answer": "模型服务暂不可用，请稍后重试。",
                "traces": [
                    {"step": 1, "type": "error", "summary": "模型服务暂不可用"}
                ],
                "sources": [],
                "audio_url": None,
                "request_id": "request-error",
            },
        )
    )

    result = ChatApiClient(transport=transport).ask("你好")

    assert result.success is False
    assert result.status_code == 503
    assert result.payload.request_id == "request-error"
    assert result.payload.traces[0].type == "error"


def test_frontend_client_converts_connection_failure_to_short_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = ChatApiClient(transport=httpx.MockTransport(handler))

    assert client.health() is False
    with pytest.raises(FrontendServiceError, match="无法连接后端服务"):
        client.ask("你好")


def test_frontend_client_rejects_invalid_response_contract() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"unexpected": "payload"})
    )

    with pytest.raises(FrontendServiceError, match="返回格式异常"):
        ChatApiClient(transport=transport).ask("你好")


def test_frontend_health_rejects_non_object_payload() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=[{"status": "ok"}])
    )

    assert ChatApiClient(transport=transport).health() is False
