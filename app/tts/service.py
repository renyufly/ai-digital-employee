"""On-demand Edge TTS synthesis and local audio lifecycle helpers."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path
import time
from typing import Protocol
from uuid import uuid4

import edge_tts

from app.core.config import Settings, get_settings
from app.core.errors import TTSServiceError


logger = logging.getLogger(__name__)


class EdgeCommunicator(Protocol):
    async def save(self, audio_fname: str) -> None: ...


CommunicatorFactory = Callable[[str, str], EdgeCommunicator]


def cleanup_expired_audio(audio_dir: Path, retention_hours: float) -> int:
    """Delete only expired MP3 files from the configured audio directory."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - retention_hours * 60 * 60
    removed = 0
    for audio_path in audio_dir.glob("*.mp3"):
        try:
            if audio_path.is_file() and audio_path.stat().st_mtime < cutoff:
                audio_path.unlink()
                removed += 1
        except OSError:
            logger.warning("Unable to inspect or remove expired audio file=%s", audio_path)
    return removed


class TTSService:
    """Generate one MP3 per accepted request without affecting chat state."""

    def __init__(
        self,
        settings: Settings | None = None,
        communicator_factory: CommunicatorFactory | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.communicator_factory = communicator_factory or edge_tts.Communicate

    async def synthesize(self, text: str) -> Path:
        """Synthesize text to a UUID-named local MP3 and return its path."""
        self.settings.audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = self.settings.audio_dir / f"{uuid4()}.mp3"
        communicator = self.communicator_factory(text, self.settings.tts_voice)

        try:
            async with asyncio.timeout(self.settings.tts_timeout_seconds):
                await communicator.save(str(audio_path))
            if not audio_path.is_file() or audio_path.stat().st_size == 0:
                raise TTSServiceError("TTS_EMPTY_AUDIO", "语音服务未返回有效音频，请稍后重试")
            return audio_path
        except TimeoutError as exc:
            self._remove_partial_file(audio_path)
            raise TTSServiceError("TTS_TIMEOUT", "语音生成超时，请稍后重试") from exc
        except TTSServiceError:
            self._remove_partial_file(audio_path)
            raise
        except Exception as exc:
            self._remove_partial_file(audio_path)
            logger.warning("Edge TTS synthesis failed: %s", type(exc).__name__)
            raise TTSServiceError("TTS_PROVIDER_ERROR", "语音生成失败，请稍后重试") from exc

    @staticmethod
    def _remove_partial_file(audio_path: Path) -> None:
        try:
            audio_path.unlink(missing_ok=True)
        except OSError:
            logger.warning("Unable to remove partial audio file=%s", audio_path)
