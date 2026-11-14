"""All-Sarvam voice agent: Saaras v3 streaming STT + Sarvam LLM
(streaming, reasoning disabled for latency) + Bulbul v3 streaming TTS.

Everything streams: STT has server-side VAD (high sensitivity = 0.5s
end-of-turn), LLM tokens flow into TTS sentence-by-sentence, and the TTS
connection opens in parallel with the LLM request.

Browser <-> backend protocol on `/ws`:
  * browser -> server: binary frames of 16 kHz mono PCM s16le audio
  * server -> browser: binary frames of 24 kHz mono PCM s16le agent audio, and
    JSON events: ConversationText, UserStartedSpeaking, Latency,
    AgentAudioDone, Error
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import time
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sarvamai import AsyncSarvamAI

from config import ALLOWED_LLM_MODELS, settings
from language import choose_tts_language
from llm import LLMError, stream_llm
from tts import FLUSH_MESSAGE, SentenceChunker, connect_tts, text_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("voice_agent")

SYSTEM_PROMPT = (
    "You are a warm, friendly voice assistant for users in India, speaking "
    "like a helpful human on a phone call. Reply in the same language the "
    "user speaks (Hindi, English, Hinglish or any Indian language). Keep "
    "answers to one or two short, natural conversational sentences — they "
    "will be spoken aloud. Vary your phrasing; sound engaged, not scripted. "
    "Never use markdown, lists or headings."
)

# Keep the system prompt plus this many recent messages to bound prompt size.
MAX_HISTORY_MESSAGES = 40
# Upper bound on waiting for the TTS engine to finish after the last text.
TTS_DRAIN_TIMEOUT_S = 30

app = FastAPI(title="Sarvam Voice Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "sarvam_key": bool(settings.sarvam_api_key)}


def origin_allowed(origin: str | None) -> bool:
    """Websockets bypass CORS, so check the Origin header explicitly.

    Requests without an Origin header (non-browser clients) are allowed.
    """
    if origin is None or "*" in settings.allowed_origins:
        return True
    return origin in settings.allowed_origins


def add_user_turn(history: list[dict[str, Any]], text: str) -> None:
    """Append a user message, merging with a previous unanswered one (barge-in)."""
    if history and history[-1]["role"] == "user":
        history[-1] = {"role": "user", "content": f"{history[-1]['content']} {text}"}
    else:
        history.append({"role": "user", "content": text})
    overflow = len(history) - 1 - MAX_HISTORY_MESSAGES
    if overflow > 0:
        del history[1 : 1 + overflow]


class CallSession:
    """State and pipeline for one browser call."""

    def __init__(self, client_ws: WebSocket, llm_model: str, api_key: str) -> None:
        self.client_ws = client_ws
        self.llm_model = llm_model
        self.api_key = api_key
        self.history: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.generation = 0
        self.respond_task: asyncio.Task | None = None

    async def send_event(self, payload: dict[str, Any]) -> None:
        with contextlib.suppress(WebSocketDisconnect, RuntimeError):
            await self.client_ws.send_json(payload)

    def interrupt(self) -> bool:
        """Cancel the in-flight reply, if any. Returns True if one was cancelled."""
        self.generation += 1
        if self.respond_task and not self.respond_task.done():
            self.respond_task.cancel()
            return True
        return False

    def start_reply(self, transcript: str, stt_language: str | None) -> None:
        self.interrupt()
        self.respond_task = asyncio.create_task(
            self.respond(transcript, stt_language, self.generation)
        )

    async def respond(self, user_text: str, stt_language: str | None, my_gen: int) -> None:
        try:
            await self._respond(user_text, stt_language, my_gen)
        except asyncio.CancelledError:
            raise
        except LLMError as exc:
            await self.send_event({"type": "Error", "description": str(exc)})
        except Exception:
            logger.exception("Reply generation failed")
            await self.send_event({"type": "Error", "description": "Failed to generate a reply"})

    async def _respond(self, user_text: str, stt_language: str | None, my_gen: int) -> None:
        start_time = time.monotonic()
        add_user_turn(self.history, user_text)
        messages = list(self.history)
        reply_parts: list[str] = []

        language = choose_tts_language(stt_language, user_text, default=settings.tts_language)
        tts_task = asyncio.create_task(connect_tts(language, settings.tts_speaker, self.api_key))
        llm = stream_llm(messages, self.llm_model, self.api_key)
        tts = None
        audio_task: asyncio.Task | None = None
        try:
            try:
                first = await llm.__anext__()
            except StopAsyncIteration:
                first = None
            if first is None:
                return  # nothing to say

            tts = await tts_task

            async def forward_audio() -> None:
                first_audio_sent = False
                async for raw in tts:
                    if self.generation != my_gen:
                        return
                    msg = json.loads(raw)
                    msg_type = msg.get("type")
                    data = msg.get("data") or {}
                    if msg_type == "audio":
                        if not first_audio_sent:
                            latency_ms = int((time.monotonic() - start_time) * 1000)
                            await self.send_event({"type": "Latency", "latency_ms": latency_ms})
                            first_audio_sent = True
                        await self.client_ws.send_bytes(base64.b64decode(data["audio"]))
                    elif msg_type == "event" and data.get("event_type") == "final":
                        return
                    elif msg_type == "error":
                        logger.error("TTS error: %s", data)
                        await self.send_event(
                            {"type": "Error", "description": data.get("message", "TTS error")}
                        )
                        return

            audio_task = asyncio.create_task(forward_audio())
            chunker = SentenceChunker()

            async def consume(delta: str) -> None:
                reply_parts.append(delta)
                ready = chunker.feed(delta)
                if ready:
                    await tts.send(text_message(ready))

            await consume(first)
            async for delta in llm:
                if self.generation != my_gen:
                    break
                await consume(delta)

            if self.generation == my_gen:
                rest = chunker.flush()
                if rest:
                    await tts.send(text_message(rest))
                await tts.send(FLUSH_MESSAGE)
                await asyncio.wait_for(audio_task, timeout=TTS_DRAIN_TIMEOUT_S)
        finally:
            await llm.aclose()
            if audio_task and not audio_task.done():
                audio_task.cancel()
            if tts is None:
                tts_task.cancel()
                with contextlib.suppress(BaseException):
                    tts = await tts_task
            if tts is not None:
                await tts.close()

        reply = "".join(reply_parts)
        if self.generation == my_gen and reply:
            self.history.append({"role": "assistant", "content": reply})
            await self.send_event(
                {"type": "ConversationText", "role": "assistant", "content": reply}
            )
            await self.send_event({"type": "AgentAudioDone"})

    async def browser_to_stt(self, stt: Any) -> None:
        while True:
            message = await self.client_ws.receive()
            if message.get("type") == "websocket.disconnect":
                return
            audio = message.get("bytes")
            if audio:
                await stt.transcribe(
                    audio=base64.b64encode(audio).decode(),
                    encoding="audio/wav",  # SDK literal; raw PCM is set via input_audio_codec
                    sample_rate=16000,
                )

    async def stt_loop(self, stt: Any) -> None:
        while True:
            resp = await stt.recv()
            rtype = getattr(resp, "type", None)
            data = getattr(resp, "data", None)
            if rtype == "events":
                signal = getattr(data, "signal_type", "") or ""
                if "START" in signal and self.interrupt():
                    await self.send_event({"type": "UserStartedSpeaking"})
                continue
            if rtype == "error":
                logger.error("STT error: %s", data)
                continue
            transcript = (getattr(data, "transcript", "") or "").strip()
            if not transcript:
                continue
            await self.send_event(
                {"type": "ConversationText", "role": "user", "content": transcript}
            )
            self.start_reply(transcript, getattr(data, "language_code", None))

    async def run(self) -> None:
        sarvam = AsyncSarvamAI(api_subscription_key=self.api_key)
        async with sarvam.speech_to_text_streaming.connect(
            model="saaras:v3",
            mode="transcribe",
            language_code=settings.stt_language,
            sample_rate="16000",
            input_audio_codec="pcm_s16le",
            vad_signals="true",
            high_vad_sensitivity="true",  # 0.5s end-of-turn silence boundary
        ) as stt:
            tasks = [
                asyncio.create_task(self.browser_to_stt(stt)),
                asyncio.create_task(self.stt_loop(stt)),
            ]
            try:
                done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    exc = task.exception()
                    if exc and not isinstance(exc, WebSocketDisconnect):
                        logger.error("Call pipeline stopped: %r", exc)
            finally:
                for task in tasks:
                    task.cancel()
                self.interrupt()


@app.websocket("/ws")
async def voice_agent(client_ws: WebSocket, llm_model: str | None = None) -> None:
    if not origin_allowed(client_ws.headers.get("origin")):
        await client_ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await client_ws.accept()

    model = llm_model or settings.llm_model
    if model not in ALLOWED_LLM_MODELS:
        await client_ws.send_json(
            {"type": "Error", "description": f"Unsupported LLM model: {model}"}
        )
        await client_ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not settings.sarvam_api_key:
        await client_ws.send_json({"type": "Error", "description": "SARVAM_API_KEY not set"})
        await client_ws.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    session = CallSession(client_ws, model, settings.sarvam_api_key)
    try:
        await session.run()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Call failed")
        await session.send_event({"type": "Error", "description": "Speech recognition unavailable"})
    finally:
        with contextlib.suppress(RuntimeError):
            await client_ws.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.host, port=settings.port)
