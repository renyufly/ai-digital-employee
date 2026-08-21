"""Streamlit UI for the AI digital employee demo."""
'''
整个项目的 Streamlit 前端页面。它不负责 Agent、RAG、RPA 的具体实现，
只负责：收集用户问题 → 调 FastAPI 后端 → 展示回答、来源、执行轨迹和 TTS 音频
'''
'''
只负责 UI 状态管理和结果展示，
真正的 Agent、RAG 和 Playwright RPA 全部在后端，
前端通过 HTTP API 与后端解耦.
'''

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

import streamlit as st

from frontend.client import ChatApiClient, FrontendServiceError

# 提前准备的 3 个演示问题
EXAMPLE_QUESTIONS = (
    "公司的退款政策是什么？",
    "帮我查询订单 10001。",
    (
        "查询订单 10001，如果已经发货，告诉我物流信息，"
        "同时根据公司的退款政策告诉我是否还能申请退款。"
    ),
)


def get_client() -> ChatApiClient:
    '''
    创建访问 FastAPI 的 HTTP 客户端，并保存在 session_state 中，
    避免 Streamlit 每次刷新页面都重新创建.
    '''
    """Keep the HTTP dependency replaceable in Streamlit's session for UI tests."""

    if "chat_client" not in st.session_state:
        st.session_state.chat_client = ChatApiClient(
            os.getenv("BACKEND_URL", "http://localhost:8000")
        )
    return st.session_state.chat_client


def initialize_state() -> None:
    '''
    初始化页面状态:
    messages：保存当前网页里的聊天记录.
    ui_session_id：给当前 UI 会话一个唯一 ID.
    注意：当前项目的 session_id 还没有真正的服务端聊天记忆，所以 UI 有历史 ≠ Agent 有上下文记忆
    '''
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("ui_session_id", str(uuid4()))


def render_sources(sources: list[dict[str, Any]]) -> None:
    '''
    展示 RAG 来源, 让回答可追踪
    '''
    if not sources:
        return
    with st.expander(f"参考来源（{len(sources)}）", expanded=False):
        for index, source in enumerate(sources, start=1):
            page = source.get("page")
            location = source.get("file", "未知文件")
            if page is not None:
                location += f" · 第 {page} 页"
            st.markdown(f"**{index}. {location}**")
            st.caption(
                f"Chunk: {source.get('chunk_id', '-')} · "
                f"相似度: {float(source.get('score', 0)):.3f}"
            )
            st.write(source.get("content", ""))


def render_history() -> None:
    '''
    渲染聊天记录
    '''
    if not st.session_state.messages:
        st.info("请选择示例问题，或在下方输入一个业务问题。")
        return

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message.get("error"):
                st.error(message["content"])
            else:
                st.markdown(message["content"])
            if message["role"] == "assistant":
                render_sources(message.get("sources", []))
                if message.get("error"):
                    continue
                audio_url = message.get("audio_url")
                if audio_url:
                    st.audio(
                        get_client().resolve_audio_url(audio_url),
                        format="audio/mpeg",
                    )
                    st.caption("语音已生成并保存在本地；页面刷新不会重复生成。")
                elif st.button(
                    "🔊 生成语音",
                    key=f"tts-{message['request_id']}",
                    help="按需将这条 AI 回答转换为中文语音。",
                ):
                    generate_speech(message)
                    st.rerun()
                if message.get("tts_error"):
                    st.warning(message["tts_error"])


def latest_assistant_message() -> dict[str, Any] | None:
    '''
    从聊天历史倒着找, 找到最近一次 AI 回答.
    主要是给右侧的 Agent Trace 面板使用
    '''
    for message in reversed(st.session_state.messages):
        if message["role"] == "assistant":
            return message
    return None


def render_trace_panel() -> None:
    '''
    展示 Agent 执行过程: 可解释 Agent UI
    '''

    st.subheader("Agent 执行轨迹")
    latest = latest_assistant_message()
    if latest is None:
        st.caption("提交问题后，这里会显示本次 Agent 与工具步骤。")
        return

    traces = latest.get("traces", [])
    if not traces:
        st.caption("本次响应没有执行轨迹。")
    for trace in traces:
        is_error = trace.get("type") == "error"
        icon = "❌" if is_error else "✅"
        name = trace.get("name") or "Agent"
        duration = trace.get("duration_ms")
        duration_text = f" · {duration} ms" if duration is not None else ""
        st.markdown(
            f"**{icon} 步骤 {trace.get('step', '-')} · {name}**{duration_text}"
        )
        st.caption(trace.get("summary", ""))

    request_id = latest.get("request_id")
    if request_id:
        st.divider()
        st.caption(f"Request ID: {request_id}")


def submit_question(client: ChatApiClient, question: str) -> None:
    '''
    发送用户问题
    '''
    """Append both sides of one UI turn; backend still receives only this question."""
    st.session_state.messages.append({"role": "user", "content": question})
    try:
        result = client.ask(question, session_id=st.session_state.ui_session_id)
        payload = result.payload.model_dump(mode="json")
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": payload["answer"],
                "traces": payload["traces"],
                "sources": payload["sources"],
                "request_id": payload["request_id"],
                "error": not result.success,
                "audio_url": payload["audio_url"],
            }
        )
    except FrontendServiceError as exc:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": str(exc),
                "traces": [],
                "sources": [],
                "request_id": f"frontend-{uuid4()}",
                "error": True,
            }
        )


def generate_speech(message: dict[str, Any]) -> None:
    '''
    调用 TTS
    '''
    """Generate audio once and keep the result attached to this UI message."""
    try:
        payload = get_client().synthesize(message["content"])
        message["audio_url"] = payload.audio_url
        message.pop("tts_error", None)
    except FrontendServiceError as exc:
        message["tts_error"] = str(exc)


def main() -> None:
    '''
    整个页面入口
    '''
    st.set_page_config(
        page_title="AI 数字员工",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    initialize_state()
    client = get_client()

    st.title("🤖 AI 数字员工")
    st.caption("Agent + RAG + Playwright RPA + Calculator")
    if client.health():
        st.success("后端服务在线", icon="✅")
    else:
        st.warning("后端服务未连接；请先启动 FastAPI。", icon="⚠️")
    st.info("演示声明：所有订单和公司资料均为模拟数据。", icon="ℹ️")

    chat_column, trace_column = st.columns([3, 1], gap="large")
    selected_question: str | None = None

    with chat_column:
        st.subheader("业务助手")
        st.caption("示例问题")
        example_columns = st.columns(3)
        labels = ("退款政策", "查询订单", "订单 + 退款政策")
        for column, label, question in zip(
            example_columns, labels, EXAMPLE_QUESTIONS, strict=True
        ):
            if column.button(label, use_container_width=True):
                selected_question = question

        render_history()
        typed_question = st.chat_input(
            "输入问题，例如：订单金额 1280 元，退款 80% 是多少？",
            max_chars=2_000,
        )

    question = typed_question or selected_question
    if question:
        with st.spinner("Agent 正在处理，订单查询可能需要启动 ERP 浏览器…"):
            submit_question(client, question)
        st.rerun()

    with trace_column:
        render_trace_panel()


if __name__ == "__main__":
    main()
