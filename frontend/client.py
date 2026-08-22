"""HTTP-only client used by the Streamlit frontend."""
'''
Streamlit 前端专门用来访问 FastAPI 后端的 HTTP 客户端。
它把“发请求、校验响应、处理异常”都封装起来，
让 UI 不需要直接接触 Agent、RAG、RPA 的内部代码
'''

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


DEFAULT_BACKEND_URL = "http://localhost:8000"
DEFAULT_CHAT_TIMEOUT_SECONDS = 120.0
DEFAULT_HEALTH_TIMEOUT_SECONDS = 2.0
DEFAULT_TTS_TIMEOUT_SECONDS = 35.0


class TraceItem(BaseModel):
    '''
    Pydantic 类：规定后端返回什么.
    表示一条 Agent 执行轨迹
    '''
    """Frontend copy of the public Agent trace contract."""

    model_config = ConfigDict(extra="ignore")

    step: int
    type: str
    name: str | None = None
    summary: str
    duration_ms: int | None = None


class SourceItem(BaseModel):
    '''
    表示 RAG 检索来源
    '''
    """Frontend copy of the public knowledge source contract."""

    model_config = ConfigDict(extra="ignore")

    file: str
    page: int | None = None
    chunk_id: str
    content: str
    score: float


class ChatPayload(BaseModel):
    '''
    规定 /api/chat 完整返回格式
    '''
    """Validated payload returned by POST /api/chat."""

    model_config = ConfigDict(extra="ignore")

    answer: str
    traces: list[TraceItem] = Field(default_factory=list)
    sources: list[SourceItem] = Field(default_factory=list)
    audio_url: str | None = None
    request_id: str


@dataclass(frozen=True, slots=True)
class ChatResult:
    '''
    除了保存后端返回的数据，还额外保存：
        HTTP 是否成功
        HTTP 状态码
    '''
    """A validated response plus whether the backend used a success status."""

    payload: ChatPayload
    success: bool
    status_code: int


class TTSPayload(BaseModel):
    '''
    TTS 返回格式
    '''
    """Validated payload returned by POST /api/tts."""

    model_config = ConfigDict(extra="ignore")

    audio_url: str
    request_id: str

    @field_validator("audio_url")
    @classmethod
    def _validate_audio_path(cls, value: str) -> str:
        '''
        专门校验: 只接受：/audio/xxx.mp3
        '''
        if not value.startswith("/audio/"):
            raise ValueError("audio_url must use the backend audio path")
        return value


class FrontendServiceError(RuntimeError):
    '''
    Streamlit 只需要处理一种项目自己的异常类型
    '''
    """Short, user-facing error for connectivity or invalid backend responses."""


class ChatApiClient:
    """Call the backend without importing any Agent, RAG, or RPA implementation."""

    def __init__(
        self,
        backend_url: str = DEFAULT_BACKEND_URL,
        *,
        chat_timeout_seconds: float = DEFAULT_CHAT_TIMEOUT_SECONDS,
        health_timeout_seconds: float = DEFAULT_HEALTH_TIMEOUT_SECONDS,
        tts_timeout_seconds: float = DEFAULT_TTS_TIMEOUT_SECONDS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.backend_url = backend_url.rstrip("/")
        self.chat_timeout_seconds = chat_timeout_seconds
        self.health_timeout_seconds = health_timeout_seconds
        self.tts_timeout_seconds = tts_timeout_seconds
        self.transport = transport

    def health(self) -> bool:
        '''
        检查后端是否正常可用.
        '''
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
        ''' 核心： 发送聊天问题 '''
        """Submit one independent question and validate the shared response contract."""

        body: dict[str, Any] = {"message": message}
        if session_id:
            body["session_id"] = session_id

        try:
            with self._client(self.chat_timeout_seconds) as client:
                ''' 向后端FastAPI发送
                POST http://localhost:8000/api/chat
                {
                    "message": "查询订单 10001",
                    "session_id": "xxx"
                }
                '''
                response = client.post("/api/chat", json=body)

        except httpx.TimeoutException as exc:
            '''
            请求超时，例如 RPA 查询 ERP 太慢
            '''
            raise FrontendServiceError(
                "请求处理超时。订单查询可能较慢，请确认 ERP 和后端状态后重试。"
            ) from exc
        except httpx.ConnectError as exc:
            '''
            FastAPI 没启动
            '''
            raise FrontendServiceError(
                "无法连接后端服务，请确认 FastAPI 已在 http://localhost:8000 启动。"
            ) from exc
        except httpx.HTTPError as exc:
            raise FrontendServiceError("后端通信失败，请稍后重试。") from exc

        try:
            '''
            前端第二次数据校验, Pydantic 发现格式符合约定
            '''
            payload = ChatPayload.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise FrontendServiceError("后端返回格式异常，请查看后端日志。") from exc

        return ChatResult(
            payload=payload,
            success=response.is_success,
            status_code=response.status_code,
        )

    def synthesize(self, text: str) -> TTSPayload:
        '''
        调用 TTS
        '''
        """Generate speech for one existing assistant answer."""
        try:
            with self._client(self.tts_timeout_seconds) as client:
                response = client.post("/api/tts", json={"text": text})
        
        except httpx.TimeoutException as exc:
            raise FrontendServiceError("语音生成超时，文字回答不受影响，请稍后重试。") from exc
        except httpx.ConnectError as exc:
            raise FrontendServiceError("无法连接语音服务，文字回答不受影响。") from exc
        except httpx.HTTPError as exc:
            raise FrontendServiceError("语音服务通信失败，文字回答不受影响。") from exc

        if not response.is_success:
            try:
                detail = response.json().get("detail")
            except (ValueError, AttributeError):
                detail = None
            raise FrontendServiceError(
                detail if isinstance(detail, str) else "语音生成失败，文字回答不受影响。"
            )

        try:
            return TTSPayload.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise FrontendServiceError("语音服务返回格式异常，文字回答不受影响。") from exc

    def resolve_audio_url(self, audio_url: str) -> str:
        '''
        把相对地址变完整地址
        '''
        """Convert the backend's safe relative audio path to a browser URL."""
        return urljoin(f"{self.backend_url}/", audio_url.lstrip("/"))

    def _client(self, timeout_seconds: float) -> httpx.Client:
        '''
        统一创建 httpx Client
        '''
        return httpx.Client(
            base_url=self.backend_url,
            timeout=httpx.Timeout(timeout_seconds),
            transport=self.transport,
        )
