"""Small OpenRouter client isolated from the agent business logic."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
import re
from time import perf_counter
from typing import Any

import openai
from openai import AsyncOpenAI

from app.core.config import Settings, get_settings
from app.core.errors import LLMConfigurationError, LLMRequestError


logger = logging.getLogger(__name__)
_MODEL_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._:-]*$")


@dataclass(frozen=True)
class LLMToolCall:
    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class LLMResponse:
    content: str | None
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    model: str | None = None
    usage: dict[str, int | None] = field(default_factory=dict)


class LLMClient:
    """Call OpenRouter through the OpenAI SDK and normalize its response."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        sdk_client: AsyncOpenAI | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._validate_configuration()
        api_key = self.settings.require_llm_api_key().strip()
        self._client = sdk_client or AsyncOpenAI(
            api_key=api_key,
            base_url=self.settings.llm_base_url,
            timeout=self.settings.llm_timeout_seconds,
            max_retries=0,
            default_headers={
                "HTTP-Referer": self.settings.openrouter_http_referer,
                "X-OpenRouter-Title": self.settings.openrouter_app_title,
            },
        )

    def _validate_configuration(self) -> None:
        if self.settings.llm_provider.lower() != "openrouter":
            raise LLMConfigurationError("LLM_PROVIDER 当前仅支持 openrouter")
        try:
            self.settings.require_llm_api_key()
        except ValueError as exc:
            raise LLMConfigurationError(
                "缺少 OPENROUTER_API_KEY，请在项目根目录 .env 中填写"
            ) from exc
        model = self.settings.llm_model.strip()
        if not model:
            raise LLMConfigurationError("缺少 LLM_MODEL，请在项目根目录 .env 中填写")
        if not _MODEL_ID_PATTERN.fullmatch(model) or model in {"openrouter/auto", "openrouter/free"}:
            raise LLMConfigurationError(
                "LLM_MODEL 必须是固定的 OpenRouter 完整模型 ID（provider/model）"
            )

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        """Make one completion request with bounded retries for transient failures."""
        attempts = self.settings.llm_max_retries + 1
        for attempt in range(attempts):
            started = perf_counter()
            try:
                response = await self._client.chat.completions.create(
                    model=self.settings.llm_model,
                    messages=messages,  # type: ignore[arg-type]
                    tools=tools,  # type: ignore[arg-type]
                    temperature=self.settings.llm_temperature,
                    max_tokens=self.settings.llm_max_output_tokens,
                    parallel_tool_calls=self.settings.llm_parallel_tool_calls,
                )
                normalized = self._normalize_response(response)
                logger.info(
                    "LLM request completed duration_ms=%d model=%s prompt_tokens=%s completion_tokens=%s",
                    round((perf_counter() - started) * 1000),
                    normalized.model or "unknown",
                    normalized.usage.get("prompt_tokens"),
                    normalized.usage.get("completion_tokens"),
                )
                return normalized
            except Exception as exc:
                mapped = self._map_error(exc)
                logger.warning(
                    "LLM request failed duration_ms=%d code=%s attempt=%d/%d",
                    round((perf_counter() - started) * 1000),
                    mapped.code,
                    attempt + 1,
                    attempts,
                )
                if not mapped.retryable or attempt + 1 >= attempts:
                    raise mapped from exc
                await asyncio.sleep(0.25 * (attempt + 1))
        raise AssertionError("unreachable")

    @staticmethod
    def _normalize_response(response: Any) -> LLMResponse:
        if not getattr(response, "choices", None):
            raise LLMRequestError("LLM_EMPTY_RESPONSE", "模型返回了空响应")
        message = response.choices[0].message
        calls = [
            LLMToolCall(
                id=call.id,
                name=call.function.name,
                arguments=call.function.arguments,
            )
            for call in (message.tool_calls or [])
        ]
        usage_obj = getattr(response, "usage", None)
        usage = {
            "prompt_tokens": getattr(usage_obj, "prompt_tokens", None),
            "completion_tokens": getattr(usage_obj, "completion_tokens", None),
            "total_tokens": getattr(usage_obj, "total_tokens", None),
        }
        return LLMResponse(
            content=message.content,
            tool_calls=calls,
            model=getattr(response, "model", None),
            usage=usage,
        )

    @staticmethod
    def _map_error(exc: Exception) -> LLMRequestError:
        if isinstance(exc, LLMRequestError):
            return exc
        if isinstance(exc, openai.AuthenticationError):
            return LLMRequestError("LLM_AUTH_FAILED", "OpenRouter API Key 无效或无权限")
        if isinstance(exc, openai.RateLimitError):
            return LLMRequestError("LLM_RATE_LIMITED", "OpenRouter 请求过于频繁，请稍后重试", retryable=True)
        if isinstance(exc, openai.APITimeoutError):
            return LLMRequestError("LLM_TIMEOUT", "OpenRouter 请求超时", retryable=True)
        if isinstance(exc, openai.APIConnectionError):
            return LLMRequestError("LLM_NETWORK_ERROR", "无法连接 OpenRouter", retryable=True)
        if isinstance(exc, openai.APIStatusError):
            status = exc.status_code
            detail = str(exc).lower()
            if status == 402:
                return LLMRequestError("LLM_INSUFFICIENT_CREDITS", "OpenRouter 余额或免费额度不足")
            if status == 404:
                return LLMRequestError(
                    "LLM_MODEL_NOT_FOUND",
                    "所选 LLM_MODEL 不存在或已下线，请在 .env 中更换当前可用模型",
                )
            if status == 400 and ("tool" in detail or "model" in detail):
                return LLMRequestError(
                    "LLM_MODEL_UNSUPPORTED",
                    "所选 LLM_MODEL 无效或不支持 Tool Calling，请更换模型",
                )
            if status >= 500:
                return LLMRequestError("LLM_PROVIDER_ERROR", "OpenRouter 上游服务暂时不可用", retryable=True)
            return LLMRequestError("LLM_API_ERROR", f"OpenRouter 请求失败（HTTP {status}）")
        return LLMRequestError("LLM_UNEXPECTED_ERROR", "LLM 调用发生未预期错误")
