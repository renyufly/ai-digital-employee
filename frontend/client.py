"""HTTP-only client used by the Streamlit frontend."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError


DEFAULT_BACKEND_URL = "http://localhost:8000"
DEFAULT_CHAT_TIMEOUT_SECONDS = 120.0
DEFAULT_HEALTH_TIMEOUT_SECONDS = 2.0


class TraceItem(BaseModel):
    """Frontend copy of the public Agent trace contract."""

    model_config = ConfigDict(extra="ignore")

    step: int
    type: str
    name: str | None = None
    summary: str
    duration_ms: int | None = None


class SourceItem(BaseModel):
    """Frontend copy of the public knowledge source contract."""

    model_config = ConfigDict(extra="ignore")

    file: str
    page: int | None = None
    chunk_id: str
    content: str
    score: float


class ChatPayload(BaseModel):
    """Validated payload returned by POST /api/chat."""

    model_config = ConfigDict(extra="ignore")

    answer: str
    traces: list[TraceItem] = Field(default_factory=list)
    sources: list[SourceItem] = Field(default_factory=list)
    audio_url: str | None = None
    request_id: str


@dataclass(frozen=True, slots=True)
class ChatResult:
    """A validated response plus whether the backend used a success status."""

    payload: ChatPayload
    success: bool
    status_code: int


class FrontendServiceError(RuntimeError):
    """Short, user-facing error for connectivity or invalid backend responses."""


class ChatApiClient:
    """Call the backend without importing any Agent, RAG, or RPA implementation."""

    def __init__(
        self,
        backend_url: str = DEFAULT_BACKEND_URL,
        *,
        chat_timeout_seconds: float = DEFAULT_CHAT_TIMEOUT_SECONDS,
        health_timeout_seconds: float = DEFAULT_HEALTH_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.backend_url = backend_url.rstrip("/")
        self.chat_timeout_seconds = chat_timeout_seconds
        self.health_timeout_seconds = health_timeout_seconds
        self.transport = transport

    def health(self) -> bool:
        """Return False for every unavailable or malformed health response."""
        try:
            with self._client(self.health_timeout_seconds) as client:
                response = client.get("/health")
            if response.status_code != 200:
                return False
            payload = response.json()
            return isinstance(payload, dict) and payload.get("status") == "ok"
        except (httpx.HTTPError, ValueError, TypeError):
            return False

    def ask(self, message: str, session_id: str | None = None) -> ChatResult:
        """Submit one independent question and validate the shared response contract."""
        body: dict[str, Any] = {"message": message}
        if session_id:
            body["session_id"] = session_id

        try:
            with self._client(self.chat_timeout_seconds) as client:
                response = client.post("/api/chat", json=body)
        except httpx.TimeoutException as exc:
            raise FrontendServiceError(
                "请求处理超时。订单查询可能较慢，请确认 ERP 和后端状态后重试。"
            ) from exc
        except httpx.ConnectError as exc:
            raise FrontendServiceError(
                "无法连接后端服务，请确认 FastAPI 已在 http://localhost:8000 启动。"
            ) from exc
        except httpx.HTTPError as exc:
            raise FrontendServiceError("后端通信失败，请稍后重试。") from exc

        try:
            payload = ChatPayload.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise FrontendServiceError("后端返回格式异常，请查看后端日志。") from exc

        return ChatResult(
            payload=payload,
            success=response.is_success,
            status_code=response.status_code,
        )

    def _client(self, timeout_seconds: float) -> httpx.Client:
        return httpx.Client(
            base_url=self.backend_url,
            timeout=httpx.Timeout(timeout_seconds),
            transport=self.transport,
        )
