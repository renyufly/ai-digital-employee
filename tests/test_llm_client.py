from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest

from app.core.config import Settings
from app.core.errors import LLMConfigurationError
from app.core.errors import LLMRequestError
from app.llm.client import LLMClient


def settings(**overrides: Any) -> Settings:
    values = {
        "openrouter_api_key": "test-key",
        "llm_model": "openai/gpt-oss-20b:free",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


class FakeCompletions:
    def __init__(self, response: object) -> None:
        self.response = response
        self.kwargs: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> object:
        self.kwargs = kwargs
        return self.response


class FakeSDK:
    def __init__(self, response: object) -> None:
        self.completions = FakeCompletions(response)
        self.chat = SimpleNamespace(completions=self.completions)


def response_with_tool() -> object:
    function = SimpleNamespace(name="calculate", arguments='{"expression":"2+2"}')
    call = SimpleNamespace(id="call-1", function=function)
    message = SimpleNamespace(content=None, tool_calls=[call])
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=4, total_tokens=14)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message)], model="qwen/test:free", usage=usage
    )


def test_llm_client_requires_api_key_and_fixed_model_id() -> None:
    with pytest.raises(LLMConfigurationError, match="OPENROUTER_API_KEY"):
        LLMClient(settings(openrouter_api_key=""))
    with pytest.raises(LLMConfigurationError, match="完整模型 ID"):
        LLMClient(settings(llm_model="openrouter/free"))
    with pytest.raises(LLMConfigurationError, match="完整模型 ID"):
        LLMClient(settings(llm_model="auto"))


@pytest.mark.asyncio
async def test_llm_client_normalizes_tool_call_and_applies_request_settings() -> None:
    fake_sdk = FakeSDK(response_with_tool())
    client = LLMClient(settings(), sdk_client=fake_sdk)  # type: ignore[arg-type]

    result = await client.complete([{"role": "user", "content": "算一下"}], [{"type": "function"}])

    assert result.tool_calls[0].name == "calculate"
    assert result.usage["total_tokens"] == 14
    assert fake_sdk.completions.kwargs["parallel_tool_calls"] is False
    assert fake_sdk.completions.kwargs["max_tokens"] == 1000
    assert fake_sdk.completions.kwargs["model"].endswith(":free")


@pytest.mark.asyncio
async def test_llm_client_retries_only_bounded_retryable_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class FlakyCompletions:
        def __init__(self) -> None:
            self.attempts = 0

        async def create(self, **kwargs: Any) -> object:
            self.attempts += 1
            if self.attempts == 1:
                raise LLMRequestError("LLM_PROVIDER_ERROR", "暂时不可用", retryable=True)
            return response_with_tool()

    completions = FlakyCompletions()
    sdk = SimpleNamespace(chat=SimpleNamespace(completions=completions))

    async def no_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr("app.llm.client.asyncio.sleep", no_sleep)
    client = LLMClient(settings(llm_max_retries=1), sdk_client=sdk)  # type: ignore[arg-type]

    result = await client.complete([], [])

    assert result.tool_calls[0].name == "calculate"
    assert completions.attempts == 2


def test_llm_client_maps_removed_model_404_explicitly() -> None:
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    response = httpx.Response(404, request=request)
    error = openai.NotFoundError("No endpoints found", response=response, body={})

    mapped = LLMClient._map_error(error)

    assert mapped.code == "LLM_MODEL_NOT_FOUND"
    assert "不存在或已下线" in mapped.message
