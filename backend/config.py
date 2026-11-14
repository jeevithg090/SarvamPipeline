"""Runtime configuration, loaded once from environment variables / `.env`."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

# LLM models the client is allowed to request via the `llm_model` query param.
ALLOWED_LLM_MODELS: tuple[str, ...] = ("sarvam-30b", "sarvam-105b")


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    sarvam_api_key: str | None = field(default_factory=lambda: os.getenv("SARVAM_API_KEY") or None)
    tts_language: str = field(default_factory=lambda: os.getenv("SARVAM_LANGUAGE", "hi-IN"))
    tts_speaker: str = field(default_factory=lambda: os.getenv("SARVAM_SPEAKER", "shubh"))
    stt_language: str = field(default_factory=lambda: os.getenv("STT_LANGUAGE", "unknown"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "sarvam-30b"))
    allowed_origins: list[str] = field(
        default_factory=lambda: _csv(
            os.getenv("ALLOWED_ORIGINS", "http://localhost:5177,http://127.0.0.1:5177")
        )
    )
    host: str = field(default_factory=lambda: os.getenv("HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _int("PORT", 8004))


settings = Settings()
