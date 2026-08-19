"""HTTP contract for on-demand text-to-speech generation."""

from __future__ import annotations

from functools import lru_cache
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import get_settings
from app.core.errors import TTSServiceError
from app.tts.service import TTSService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["tts"])


class TTSRequest(BaseModel):
    """A bounded assistant answer selected by the frontend for synthesis."""

    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, description="已经生成的简短 AI 文字回答")

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("text 不能为空")
        max_length = get_settings().tts_max_text_length
        if len(text) > max_length:
            raise ValueError(f"text 不能超过 {max_length} 个字符")
        return text


class TTSResponse(BaseModel):
    audio_url: str
    request_id: str


class TTSErrorResponse(BaseModel):
    detail: str
    request_id: str


@lru_cache
def get_tts_service() -> TTSService:
    return TTSService()


@router.post(
    "/tts",
    response_model=TTSResponse,
    responses={
        422: {"model": TTSErrorResponse, "description": "空文本、超长文本或无效字段"},
        502: {"model": TTSErrorResponse, "description": "在线语音服务失败"},
        504: {"model": TTSErrorResponse, "description": "语音生成超时"},
    },
    summary="为已有 AI 回答按需生成中文语音",
)
async def synthesize_speech(
    payload: TTSRequest,
    request: Request,
    service: Annotated[TTSService, Depends(get_tts_service)],
) -> TTSResponse | JSONResponse:
    request_id = request.state.request_id
    logger.info("TTS request started text_length=%d", len(payload.text))
    try:
        audio_path = await service.synthesize(payload.text)
    except TTSServiceError as exc:
        status_code = 504 if exc.code == "TTS_TIMEOUT" else 502
        logger.warning("TTS request failed code=%s", exc.code)
        error = TTSErrorResponse(detail=exc.message, request_id=request_id)
        return JSONResponse(status_code=status_code, content=error.model_dump())

    response = TTSResponse(audio_url=f"/audio/{audio_path.name}", request_id=request_id)
    logger.info("TTS request completed audio_file=%s", audio_path.name)
    return response
