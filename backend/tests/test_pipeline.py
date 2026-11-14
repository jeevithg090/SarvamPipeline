"""End-to-end test of the websocket call pipeline with Sarvam services faked."""

import asyncio
import base64
import contextlib
import json
from types import SimpleNamespace
from typing import ClassVar

import pytest
from fastapi.testclient import TestClient

import main
from config import Settings


class FakeSTT:
    def __init__(self, transcripts):
        self._queue = asyncio.Queue()
        for text, lang in transcripts:
            self._queue.put_nowait(
                SimpleNamespace(
                    type="data", data=SimpleNamespace(transcript=text, language_code=lang)
                )
            )
        self.audio_frames = 0

    async def transcribe(self, audio, encoding, sample_rate):
        self.audio_frames += 1

    async def recv(self):
        return await self._queue.get()


class FakeSarvam:
    stt = None

    def __init__(self, api_subscription_key):
        self.speech_to_text_streaming = self

    @contextlib.asynccontextmanager
    async def connect(self, **kwargs):
        yield FakeSarvam.stt


class FakeTTS:
    instances: ClassVar[list["FakeTTS"]] = []

    def __init__(self, language):
        self.language = language
        self.sent = []
        self.closed = False
        self._out = asyncio.Queue()
        FakeTTS.instances.append(self)

    async def send(self, raw):
        msg = json.loads(raw)
        self.sent.append(msg)
        if msg["type"] == "text":
            audio = base64.b64encode(b"\x01\x00" * 4).decode()
            await self._out.put(json.dumps({"type": "audio", "data": {"audio": audio}}))
        elif msg["type"] == "flush":
            await self._out.put(json.dumps({"type": "event", "data": {"event_type": "final"}}))

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self._out.get()

    async def close(self):
        self.closed = True


@pytest.fixture
def fakes(monkeypatch):
    FakeTTS.instances = []
    FakeSarvam.stt = FakeSTT([("नमस्ते, मौसम कैसा है?", "unknown")])

    async def fake_connect_tts(language, speaker, api_key):
        return FakeTTS(language)

    async def fake_stream_llm(messages, model, api_key):
        assert messages[-1] == {"role": "user", "content": "नमस्ते, मौसम कैसा है?"}
        for part in ["आज ", "धूप है।", " बाहर जाने के लिए अच्छा दिन है।"]:
            yield part

    monkeypatch.setattr(main, "settings", Settings(sarvam_api_key="k", allowed_origins=["*"]))
    monkeypatch.setattr(main, "AsyncSarvamAI", FakeSarvam)
    monkeypatch.setattr(main, "connect_tts", fake_connect_tts)
    monkeypatch.setattr(main, "stream_llm", fake_stream_llm)


def test_full_turn(fakes):
    client = TestClient(main.app)
    with client.websocket_connect("/ws?llm_model=sarvam-105b") as ws:
        ws.send_bytes(b"\x00\x00" * 160)
        events = []
        audio_bytes = 0
        while True:
            message = ws.receive()
            if message.get("bytes") is not None:
                audio_bytes += len(message["bytes"])
                continue
            event = json.loads(message["text"])
            events.append(event)
            if event["type"] == "AgentAudioDone":
                break

    types = [e["type"] for e in events]
    assert types == ["ConversationText", "Latency", "ConversationText", "AgentAudioDone"]
    assert events[0] == {
        "type": "ConversationText",
        "role": "user",
        "content": "नमस्ते, मौसम कैसा है?",
    }
    assert events[2]["content"] == "आज धूप है। बाहर जाने के लिए अच्छा दिन है।"
    assert audio_bytes == 16  # two sentences x 8 bytes of fake PCM

    (tts,) = FakeTTS.instances
    assert tts.language == "hi-IN"
    assert [m["type"] for m in tts.sent] == ["text", "text", "flush"]
    assert tts.closed
