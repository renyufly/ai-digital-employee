"""Stable data contracts used across agent-facing components."""

from typing import Any

from pydantic import BaseModel, Field


class Source(BaseModel):
    """A traceable knowledge source; RPA results normally have none."""

    file: str
    page: int | None = None
    chunk_id: str
    content: str
    score: float


class ToolResult(BaseModel):
    """Uniform result returned by every tool implementation."""

    success: bool
    data: dict[str, Any] | None = None
    error_code: str | None = None
    message: str
    sources: list[Source] = Field(default_factory=list)
