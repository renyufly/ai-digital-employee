"""Stable data contracts used across agent-facing components."""

from typing import Any, Literal

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


class AgentTrace(BaseModel):
    """Short, display-safe trace entry for one agent or tool event."""

    step: int
    type: Literal["agent", "tool_start", "tool_result", "error"]
    name: str | None = None
    summary: str
    duration_ms: int | None = None


class AgentResult(BaseModel):
    """Phase 5 result; the HTTP layer will wrap it in Phase 6."""

    answer: str
    traces: list[AgentTrace] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    error_code: str | None = None
