"""Environment-backed application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration with safe local-development defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    llm_provider: str = "openrouter"
    openrouter_api_key: str | None = None
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = ""
    llm_temperature: float = Field(default=0, ge=0, le=2)
    llm_parallel_tool_calls: bool = False
    llm_timeout_seconds: float = Field(default=60, gt=0)
    llm_max_retries: int = Field(default=1, ge=0, le=5)
    llm_max_output_tokens: int = Field(default=1000, ge=1)
    openrouter_http_referer: str = "http://localhost:8501"
    openrouter_app_title: str = "AI Digital Employee Demo"
    max_agent_steps: int = Field(default=5, ge=1, le=20)

    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_cache_dir: Path = Path("./.model-cache")
    knowledge_dir: Path = Path("./knowledge")
    vector_db_path: Path = Path("./data/vector_store")
    chunk_size: int = Field(default=500, ge=100)
    chunk_overlap: int = Field(default=80, ge=0)
    rag_top_k: int = Field(default=3, ge=1)
    rag_score_threshold: float | None = Field(default=0.45, ge=-1, le=1)

    mock_erp_url: str = "http://localhost:8001"
    mock_erp_username: str = "admin"
    mock_erp_password: str = "admin123"
    mock_erp_database_path: Path = Path("./data/orders.db")
    mock_erp_session_secret: str = "local-demo-session-secret"
    rpa_headless: bool = False
    rpa_timeout_ms: int = Field(default=15_000, gt=0)
    playwright_browsers_path: Path = Path("./.playwright-browsers")

    backend_url: str = "http://localhost:8000"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    audio_dir: Path = Path("./data/audio")

    @model_validator(mode="after")
    def validate_chunk_window(self) -> "Settings":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self

    @field_validator("rag_score_threshold", mode="before")
    @classmethod
    def parse_optional_score_threshold(cls, value: object) -> object:
        if value == "":
            return None
        return value

    def require_llm_api_key(self) -> str:
        """Return the API key only when an LLM operation actually needs it."""
        if not self.openrouter_api_key or not self.openrouter_api_key.strip():
            raise ValueError("OPENROUTER_API_KEY is required for LLM operations")
        return self.openrouter_api_key


@lru_cache
def get_settings() -> Settings:
    """Load and validate settings once per process."""
    return Settings()
