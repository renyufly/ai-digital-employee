"""FastAPI entry point for the AI digital employee."""

from contextlib import asynccontextmanager
import logging
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agent.schemas import AgentTrace
from app.api.chat import ChatResponse, router as chat_router
from app.api.tts import TTSErrorResponse, router as tts_router
from app.core.config import get_settings
from app.core.errors import LLMConfigurationError
from app.core.logging import configure_logging, reset_request_id, set_request_id
from app.tts.service import cleanup_expired_audio


class HealthResponse(BaseModel):
    status: str


settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

settings.audio_dir.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    removed = cleanup_expired_audio(settings.audio_dir, settings.audio_retention_hours)
    logger.info("Audio startup cleanup completed removed=%d", removed)
    yield


app = FastAPI(title="AI Digital Employee", version="0.1.0", lifespan=lifespan)
app.include_router(chat_router)
app.include_router(tts_router)
app.mount("/audio", StaticFiles(directory=settings.audio_dir), name="audio")


@app.middleware("http")
async def add_request_id(request: Request, call_next) -> Response:
    request_id = str(uuid4())
    request.state.request_id = request_id
    token = set_request_id(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        reset_request_id(token)


def _error_response(request: Request, status_code: int, message: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    response = ChatResponse(
        answer=message,
        traces=[AgentTrace(step=0, type="error", summary=message)],
        sources=[],
        audio_url=None,
        request_id=request_id,
    )
    return JSONResponse(status_code=status_code, content=response.model_dump(mode="json"))


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.info(
        "Request validation failed path=%s error_count=%d",
        request.url.path,
        len(exc.errors()),
    )
    if request.url.path == "/api/tts":
        request_id = getattr(request.state, "request_id", str(uuid4()))
        response = TTSErrorResponse(
            detail=(
                "请求参数无效，text 必须是非空且不超过 "
                f"{settings.tts_max_text_length} 个字符的字符串"
            ),
            request_id=request_id,
        )
        return JSONResponse(status_code=422, content=response.model_dump())
    return _error_response(
        request,
        422,
        "请求参数无效，请检查 message（1 至 2000 个字符）和可选 session_id",
    )


@app.exception_handler(LLMConfigurationError)
async def llm_configuration_error_handler(
    request: Request, exc: LLMConfigurationError
) -> JSONResponse:
    logger.warning("LLM configuration unavailable: %s", exc)
    return _error_response(request, 503, str(exc))


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled chat API error")
    return _error_response(request, 500, "服务发生未预期错误，请稍后重试")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
