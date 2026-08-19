from __future__ import annotations

import asyncio
import os
from pathlib import Path
import time

import pytest

from app.core.config import Settings
from app.core.errors import TTSServiceError
from app.tts.service import TTSService, cleanup_expired_audio


class WritingCommunicator:
    def __init__(self, text: str, voice: str, calls: list[tuple[str, str]]) -> None:
        calls.append((text, voice))

    async def save(self, audio_fname: str) -> None:
        Path(audio_fname).write_bytes(b"fake-mp3")


@pytest.mark.asyncio
async def test_tts_service_writes_uuid_mp3_with_configured_voice(tmp_path: Path) -> None:
    calls: list[tuple[str, str]] = []
    settings = Settings(
        audio_dir=tmp_path,
        tts_voice="zh-CN-XiaoxiaoNeural",
        tts_timeout_seconds=1,
    )
    service = TTSService(
        settings,
        communicator_factory=lambda text, voice: WritingCommunicator(text, voice, calls),
    )

    audio_path = await service.synthesize("订单已经发货。")

    assert calls == [("订单已经发货。", "zh-CN-XiaoxiaoNeural")]
    assert audio_path.parent == tmp_path
    assert audio_path.suffix == ".mp3"
    assert len(audio_path.stem) == 36
    assert audio_path.read_bytes() == b"fake-mp3"


@pytest.mark.asyncio
async def test_tts_service_removes_partial_file_after_provider_failure(
    tmp_path: Path,
) -> None:
    class BrokenCommunicator:
        async def save(self, audio_fname: str) -> None:
            Path(audio_fname).write_bytes(b"partial")
            raise RuntimeError("provider detail must stay private")

    service = TTSService(
        Settings(audio_dir=tmp_path),
        communicator_factory=lambda text, voice: BrokenCommunicator(),
    )

    with pytest.raises(TTSServiceError, match="语音生成失败") as error:
        await service.synthesize("测试")

    assert error.value.code == "TTS_PROVIDER_ERROR"
    assert list(tmp_path.glob("*.mp3")) == []


@pytest.mark.asyncio
async def test_tts_service_times_out_without_leaving_audio(tmp_path: Path) -> None:
    class SlowCommunicator:
        async def save(self, audio_fname: str) -> None:
            Path(audio_fname).write_bytes(b"partial")
            await asyncio.sleep(1)

    service = TTSService(
        Settings(audio_dir=tmp_path, tts_timeout_seconds=0.01),
        communicator_factory=lambda text, voice: SlowCommunicator(),
    )

    with pytest.raises(TTSServiceError, match="语音生成超时") as error:
        await service.synthesize("测试")

    assert error.value.code == "TTS_TIMEOUT"
    assert list(tmp_path.glob("*.mp3")) == []


def test_cleanup_removes_only_expired_mp3_files(tmp_path: Path) -> None:
    expired = tmp_path / "expired.mp3"
    recent = tmp_path / "recent.mp3"
    unrelated = tmp_path / "keep.txt"
    for path in (expired, recent, unrelated):
        path.write_bytes(b"data")
    old_timestamp = time.time() - 25 * 60 * 60
    os.utime(expired, (old_timestamp, old_timestamp))

    removed = cleanup_expired_audio(tmp_path, retention_hours=24)

    assert removed == 1
    assert not expired.exists()
    assert recent.exists()
    assert unrelated.exists()
