from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from streamlit.testing.v1 import AppTest

from frontend.client import (
    ChatPayload,
    ChatResult,
    FrontendServiceError,
    SourceItem,
    TTSPayload,
    TraceItem,
)
from frontend.streamlit_app import EXAMPLE_QUESTIONS


APP_PATH = Path(__file__).resolve().parents[1] / "frontend" / "streamlit_app.py"


@dataclass
class FakeChatClient:
    available: bool = True
    fail: bool = False
    tts_fail: bool = False
    calls: list[tuple[str, str | None]] = field(default_factory=list)
    tts_calls: list[str] = field(default_factory=list)

    def health(self) -> bool:
        return self.available

    def ask(self, message: str, session_id: str | None = None) -> ChatResult:
        self.calls.append((message, session_id))
        if self.fail:
            raise FrontendServiceError("无法连接后端服务，请确认 FastAPI 已启动。")

        traces = [
            TraceItem(
                step=1,
                type="tool_result",
                name="query_order" if "订单" in message else "search_company_docs",
                summary="执行成功",
                duration_ms=25,
            )
        ]
        if "同时" in message:
            traces.append(
                TraceItem(
                    step=2,
                    type="tool_result",
                    name="search_company_docs",
                    summary="执行成功",
                    duration_ms=15,
                )
            )
        sources = []
        if "退款" in message:
            sources = [
                SourceItem(
                    file="refund_policy.pdf",
                    page=1,
                    chunk_id="refund-policy-p1-c1",
                    content="已发货订单需要先完成退货流程。",
                    score=0.88,
                )
            ]
        request_number = len(self.calls)
        return ChatResult(
            payload=ChatPayload(
                answer=f"测试回答 {request_number}",
                traces=traces,
                sources=sources,
                request_id=f"request-{request_number}",
            ),
            success=True,
            status_code=200,
        )

    def synthesize(self, text: str) -> TTSPayload:
        self.tts_calls.append(text)
        if self.tts_fail:
            raise FrontendServiceError("语音生成失败，文字回答不受影响。")
        return TTSPayload(audio_url="/audio/test.mp3", request_id="tts-request")

    def resolve_audio_url(self, audio_url: str) -> str:
        return f"http://localhost:8000{audio_url}"


def make_app(client: FakeChatClient) -> AppTest:
    app = AppTest.from_file(APP_PATH, default_timeout=10)
    app.session_state["chat_client"] = client
    return app.run()


def test_frontend_initial_layout_and_service_status() -> None:
    app = make_app(FakeChatClient())

    assert not app.exception
    assert [button.label for button in app.button[:3]] == [
        "退款政策",
        "查询订单",
        "订单 + 退款政策",
    ]
    assert len(app.chat_input) == 1
    assert any("所有订单和公司资料均为模拟数据" in item.value for item in app.info)
    assert any("后端服务在线" in item.value for item in app.success)
    assert any("Agent 执行轨迹" in item.value for item in app.subheader)


def test_all_examples_keep_history_and_render_sources_and_multi_tool_trace() -> None:
    app = make_app(FakeChatClient())

    for button_index in range(3):
        app.button[button_index].click().run()

    messages = app.session_state["messages"]
    client = app.session_state["chat_client"]
    assert [call[0] for call in client.calls] == list(EXAMPLE_QUESTIONS)
    assert len({call[1] for call in client.calls}) == 1
    assert len(messages) == 6
    assert len(app.chat_message) == 6
    assert any("refund_policy.pdf" in item.value for item in app.markdown)
    assert any("query_order" in item.value for item in app.markdown)
    assert any("search_company_docs" in item.value for item in app.markdown)
    assert any("Request ID: request-3" in item.value for item in app.caption)
    assert len(app.expander) == 2
    assert all(not expander.proto.expanded for expander in app.expander)


def test_repeated_typed_questions_do_not_lose_previous_ui_history() -> None:
    app = make_app(FakeChatClient())

    app.chat_input[0].set_value("相同问题").run()
    app.chat_input[0].set_value("相同问题").run()

    messages = app.session_state["messages"]
    assert len(messages) == 4
    assert [message["content"] for message in messages if message["role"] == "user"] == [
        "相同问题",
        "相同问题",
    ]


def test_backend_connection_error_is_shown_in_chat() -> None:
    app = make_app(FakeChatClient(available=False, fail=True))

    app.button[1].click().run()

    assert any("后端服务未连接" in item.value for item in app.warning)
    assert any("无法连接后端服务" in item.value for item in app.error)
    assert app.session_state["messages"][-1]["error"] is True


def test_tts_button_generates_once_and_reuses_audio_on_rerun() -> None:
    app = make_app(FakeChatClient())
    app.button[0].click().run()

    tts_button = next(button for button in app.button if button.label == "🔊 生成语音")
    tts_button.click().run()

    client = app.session_state["chat_client"]
    assistant = app.session_state["messages"][-1]
    assert not app.exception
    assert client.tts_calls == [assistant["content"]]
    assert assistant["audio_url"] == "/audio/test.mp3"
    assert any("页面刷新不会重复生成" in item.value for item in app.caption)
    assert all(button.label != "🔊 生成语音" for button in app.button)

    app.run()
    assert client.tts_calls == [assistant["content"]]


def test_tts_failure_keeps_answer_and_allows_retry() -> None:
    app = make_app(FakeChatClient(tts_fail=True))
    app.button[0].click().run()
    answer = app.session_state["messages"][-1]["content"]

    next(button for button in app.button if button.label == "🔊 生成语音").click().run()

    assistant = app.session_state["messages"][-1]
    assert assistant["content"] == answer
    assert assistant.get("audio_url") is None
    assert any("语音生成失败" in item.value for item in app.warning)
    assert any(button.label == "🔊 生成语音" for button in app.button)
