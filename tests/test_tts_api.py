from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from app.api.tts import get_tts_service
from app.core.errors import TTSServiceError
from app.main import app, settings


class FakeTTSService:
    def __init__(self, result: Path | TTSServiceError) -> None:
        self.result = result
        self.texts: list[str] = []

    async def synthesize(self, text: str) -> Path:
        self.texts.append(text)
        if isinstance(self.result, TTSServiceError):
            raise self.result
        return self.result


@pytest_asyncio.fixture
async def tts_api_client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_tts_api_returns_local_audio_url_and_request_id(
    tts_api_client: httpx.AsyncClient,
) -> None:
    fake = FakeTTSService(Path("data/audio/12345678-1234-1234-1234-123456789abc.mp3"))
    app.dependency_overrides[get_tts_service] = lambda: fake

    response = await tts_api_client.post("/api/tts", json={"text": " 订单已发货。 "})

    assert response.status_code == 200
    assert fake.texts == ["订单已发货。"]
    assert response.json()["audio_url"] == "/audio/12345678-1234-1234-1234-123456789abc.mp3"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{"text": ""}, {"text": "   "}, {"text": "x" * 2_001}, {}])
async def test_tts_api_rejects_empty_or_overlong_text(
    tts_api_client: httpx.AsyncClient, body: dict[str, str]
) -> None:
    response = await tts_api_client.post("/api/tts", json=body)

    assert response.status_code == 422
    assert set(response.json()) == {"detail", "request_id"}
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (TTSServiceError("TTS_PROVIDER_ERROR", "语音生成失败，请稍后重试"), 502),
        (TTSServiceError("TTS_TIMEOUT", "语音生成超时，请稍后重试"), 504),
    ],
)
async def test_tts_api_maps_provider_failures_without_affecting_chat_contract(
    tts_api_client: httpx.AsyncClient,
    error: TTSServiceError,
    status_code: int,
) -> None:
    app.dependency_overrides[get_tts_service] = lambda: FakeTTSService(error)

    response = await tts_api_client.post("/api/tts", json={"text": "测试回答"})

    assert response.status_code == status_code
    assert response.json()["detail"] == str(error)
    assert set(response.json()) == {"detail", "request_id"}


@pytest.mark.asyncio
async def test_audio_static_route_serves_generated_mp3(
    tts_api_client: httpx.AsyncClient,
) -> None:
    filename = f"test-{uuid4()}.mp3"
    audio_path = settings.audio_dir / filename
    audio_path.write_bytes(b"fake-mp3")
    try:
        response = await tts_api_client.get(f"/audio/{filename}")
    finally:
        audio_path.unlink(missing_ok=True)

    assert response.status_code == 200
    assert response.content == b"fake-mp3"
    assert response.headers["content-type"] == "audio/mpeg"


def test_openapi_includes_tts_endpoint() -> None:
    schema = app.openapi()

    assert "/api/tts" in schema["paths"]
    assert schema["paths"]["/api/tts"]["post"]["tags"] == ["tts"]
