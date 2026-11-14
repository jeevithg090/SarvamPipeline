"""Bulbul v3 streaming text-to-speech helpers."""

from __future__ import annotations

import json

import websockets
from websockets.asyncio.client import ClientConnection

SARVAM_TTS_URL = "wss://api.sarvam.ai/text-to-speech/ws?model=bulbul:v3&send_completion_event=true"
SAMPLE_RATE = 24000

SENTENCE_ENDINGS = (".", "!", "?", "।")


class SentenceChunker:
    """Buffers LLM deltas and releases whole sentences for the TTS engine.

    Full sentences only: comma-level fragments make the TTS prosody flat and
    robotic. The first sentence is released as soon as it ends (lowest
    latency); later ones wait for at least `min_chars` to batch short
    sentences together.
    """

    def __init__(self, min_chars: int = 40) -> None:
        self.min_chars = min_chars
        self._buffer = ""
        self._sent_first = False

    def feed(self, delta: str) -> str | None:
        """Add a delta; return text ready to synthesise, if any."""
        self._buffer += delta
        min_len = self.min_chars if self._sent_first else 1
        if self._buffer.rstrip().endswith(SENTENCE_ENDINGS) and len(self._buffer) >= min_len:
            return self._release()
        return None

    def flush(self) -> str | None:
        """Return whatever is left in the buffer."""
        return self._release()

    def _release(self) -> str | None:
        text, self._buffer = self._buffer, ""
        if not text.strip():
            return None
        self._sent_first = True
        return text


def tts_config(language: str, speaker: str) -> dict:
    return {
        "type": "config",
        "data": {
            "target_language_code": language,
            "speaker": speaker,
            "speech_sample_rate": str(SAMPLE_RATE),
            "output_audio_codec": "linear16",
            "min_buffer_size": 30,
            "max_chunk_length": 250,
            "temperature": 0.7,  # bulbul:v3 expressiveness
            "pace": 0.95,
        },
    }


async def connect_tts(language: str, speaker: str, api_key: str) -> ClientConnection:
    """Open a configured Bulbul v3 streaming TTS websocket."""
    tts = await websockets.connect(
        SARVAM_TTS_URL,
        additional_headers={"api-subscription-key": api_key},
    )
    try:
        await tts.send(json.dumps(tts_config(language, speaker)))
    except Exception:
        await tts.close()
        raise
    return tts


def text_message(text: str) -> str:
    return json.dumps({"type": "text", "data": {"text": text}})


FLUSH_MESSAGE = json.dumps({"type": "flush"})
