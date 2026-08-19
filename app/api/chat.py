"""Stable HTTP contract for the single-turn Agent chat endpoint."""

from __future__ import annotations

from functools import lru_cache
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.agent.schemas import AgentResult, AgentTrace, Source
from app.agent.service import AgentService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

MAX_CHAT_MESSAGE_LENGTH = 2_000
MAX_SESSION_ID_LENGTH = 128


class ChatRequest(BaseModel):
    """One independent question; session_id is reserved for a later phase."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"message": "退款多久到账？"},
                {"message": "帮我查询订单 10001。"},
                {
                    "message": (
                        "查询订单 10001，如果已经发货，告诉我物流信息，"
                        "同时根据公司的退款政策告诉我是否还能申请退款。"
                    ),
                    "session_id": "demo-session",
                },
            ]
        },
    )

    message: str = Field(
        min_length=1,
        max_length=MAX_CHAT_MESSAGE_LENGTH,
        description="本次独立处理的用户问题，不会读取此前对话。",
    )
    session_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_SESSION_ID_LENGTH,
        description="预留的会话标识；Phase 6 不保存或读取会话上下文。",
    )

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        message = value.strip()
        if not message:
            raise ValueError("message 不能为空")
        return message

    @field_validator("session_id")
    @classmethod
    def normalize_session_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        session_id = value.strip()
        if not session_id:
            raise ValueError("session_id 不能为空字符串")
        return session_id


class ChatResponse(BaseModel):
    """JSON-safe response shared by successful and expected-error calls."""

    answer: str
    traces: list[AgentTrace] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    audio_url: str | None = None
    request_id: str


@lru_cache
def get_agent_service() -> AgentService:
    """Reuse the stateless service while keeping it replaceable in API tests."""
    return AgentService()


def chat_response_from_result(result: AgentResult, request_id: str) -> ChatResponse:
    return ChatResponse(
        answer=result.answer,
        traces=result.traces,
        sources=result.sources,
        audio_url=None,
        request_id=request_id,
    )


def status_for_agent_result(result: AgentResult) -> int:
    """Map expected Agent failures without turning them into opaque HTTP 500s."""
    if result.error_code is None:
        return 200
    if result.error_code == "INVALID_ARGUMENT":
        return 400
    if result.error_code in {"ORDER_NOT_FOUND", "NO_RELEVANT_DOCUMENT"}:
        return 404
    if result.error_code in {"LLM_TIMEOUT", "RPA_TIMEOUT"}:
        return 504
    if result.error_code in {
        "LLM_NETWORK_ERROR",
        "LLM_PROVIDER_ERROR",
        "ERP_LOGIN_FAILED",
        "TOOL_INTERNAL_ERROR",
    }:
        return 502
    if result.error_code in {
        "LLM_AUTH_FAILED",
        "LLM_INSUFFICIENT_CREDITS",
        "LLM_MODEL_NOT_FOUND",
        "LLM_MODEL_UNSUPPORTED",
        "LLM_RATE_LIMITED",
        "RAG_NOT_READY",
    }:
        return 503
    return 422


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        400: {"model": ChatResponse, "description": "请求参数在业务层无效"},
        404: {"model": ChatResponse, "description": "订单或相关知识不存在"},
        422: {"model": ChatResponse, "description": "请求校验或 Agent 执行约束失败"},
        502: {"model": ChatResponse, "description": "上游工具或模型服务失败"},
        503: {"model": ChatResponse, "description": "模型或知识库暂不可用"},
        504: {"model": ChatResponse, "description": "模型或 RPA 执行超时"},
    },
    summary="向 AI 数字员工提交单轮问题",
    description=(
        "每次请求独立处理，不保留会话上下文。订单查询会启动本地浏览器自动化，"
        "客户端超时必须高于 RPA_TIMEOUT_MS；演示前端建议至少设置为 120 秒。"
    ),
)
async def chat(
    payload: ChatRequest,
    request: Request,
    agent_service: Annotated[AgentService, Depends(get_agent_service)],
) -> ChatResponse | JSONResponse:
    request_id = request.state.request_id
    logger.info(
        "Chat request started message_length=%d has_session_id=%s",
        len(payload.message),
        payload.session_id is not None,
    )
    result = await agent_service.run(payload.message)
    for trace in result.traces:
        logger.info(
            "Agent trace step=%d type=%s name=%s duration_ms=%s summary=%s",
            trace.step,
            trace.type,
            trace.name or "-",
            trace.duration_ms,
            trace.summary,
        )

    response = chat_response_from_result(result, request_id)
    status_code = status_for_agent_result(result)
    logger.info(
        "Chat request completed status_code=%d error_code=%s traces=%d sources=%d",
        status_code,
        result.error_code or "-",
        len(result.traces),
        len(result.sources),
    )
    if status_code == 200:
        return response
    return JSONResponse(status_code=status_code, content=response.model_dump(mode="json"))
