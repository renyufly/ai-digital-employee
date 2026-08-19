"""Minimal FastAPI entry point for Phase 0."""

from uuid import uuid4

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.logging import configure_logging, reset_request_id, set_request_id


class HealthResponse(BaseModel):
    status: str


settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="AI Digital Employee", version="0.1.0")


@app.middleware("http")
async def add_request_id(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    token = set_request_id(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        reset_request_id(token)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
