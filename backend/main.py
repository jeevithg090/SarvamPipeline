"""All-Sarvam voice agent: Saaras v3 streaming STT + Sarvam-30B LLM
(streaming, reasoning disabled for latency) + Bulbul v3 streaming TTS.

Everything streams: STT has server-side VAD (high sensitivity = 0.5s
end-of-turn), LLM tokens flow into TTS phrase-by-phrase, and the TTS
connection opens in parallel with the LLM request.
"""

import asyncio
import base64
import json
import os
import time

import httpx
import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sarvamai import AsyncSarvamAI

from agent_functions import FUNCTION_DEFINITIONS, FUNCTION_MAP

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

SARVAM_TTS_URL = "wss://api.sarvam.ai/text-to-speech/ws?model=bulbul:v3&send_completion_event=true"
SARVAM_LANGUAGE = os.getenv("SARVAM_LANGUAGE", "hi-IN")
SARVAM_SPEAKER = os.getenv("SARVAM_SPEAKER", "shubh")
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "unknown")  # unknown = auto-detect
LLM_MODEL = os.getenv("LLM_MODEL", "sarvam-30b")

SYSTEM_PROMPT = (
    "You are a warm, friendly voice assistant for users in India, speaking "
    "like a helpful human on a phone call. Reply in the same language the "
    "user speaks (Hindi, English, Hinglish or any Indian language). Keep "
    "answers to one or two short, natural conversational sentences — they "
    "will be spoken aloud. Vary your phrasing; sound engaged, not scripted. "
    "Never use markdown, lists or headings."
)

def detect_language_from_text(text: str) -> str:
    """Detect language based on Unicode script blocks."""
    char_counts = {
        "hi-IN": 0, "bn-IN": 0, "gu-IN": 0, "or-IN": 0, "ta-IN": 0, 
        "te-IN": 0, "kn-IN": 0, "ml-IN": 0, "pa-IN": 0, "en-IN": 0,
    }
    for char in text:
        code = ord(char)
        if 0x0900 <= code <= 0x097F: char_counts["hi-IN"] += 1
        elif 0x0980 <= code <= 0x09FF: char_counts["bn-IN"] += 1
        elif 0x0A80 <= code <= 0x0AFF: char_counts["gu-IN"] += 1
        elif 0x0B00 <= code <= 0x0B7F: char_counts["or-IN"] += 1
        elif 0x0B80 <= code <= 0x0BFF: char_counts["ta-IN"] += 1
        elif 0x0C00 <= code <= 0x0C7F: char_counts["te-IN"] += 1
        elif 0x0C80 <= code <= 0x0CFF: char_counts["kn-IN"] += 1
        elif 0x0D00 <= code <= 0x0D7F: char_counts["ml-IN"] += 1
        elif 0x0A00 <= code <= 0x0A7F: char_counts["pa-IN"] += 1
        elif 0x0041 <= code <= 0x005A or 0x0061 <= code <= 0x007A: char_counts["en-IN"] += 1

    max_lang = max(char_counts, key=char_counts.get)
    if char_counts[max_lang] == 0:
        return "en-IN"  # fallback
    return max_lang

OPENAI_TOOLS = [{"type": "function", "function": f} for f in FUNCTION_DEFINITIONS]

app = FastAPI(title="Sarvam Voice Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "sarvam_key": bool(SARVAM_API_KEY)}


async def stream_llm(messages: list, llm_model: str):
    """Yield reply text deltas from Sarvam chat; handles the function loop."""
    async with httpx.AsyncClient(timeout=60) as http:
        while True:
            tool_calls = {}
            async with http.stream(
                "POST",
                "https://api.sarvam.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {SARVAM_API_KEY}"},
                json={
                    "model": llm_model,
                    "messages": messages,
                    "tools": OPENAI_TOOLS,
                    "reasoning_effort": None,  # thinking off: latency-critical
                    "max_tokens": 200,
                    "stream": True,
                },
            ) as resp:
                if resp.status_code != 200:
                    text = await resp.aread()
                    print("LLM Error:", resp.status_code, text)
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    chunk = json.loads(line[6:])
                    if not chunk.get("choices"):
                        continue
                    delta = chunk["choices"][0].get("delta") or {}
                    if delta.get("content"):
                        yield delta["content"]
                    for tc in delta.get("tool_calls") or []:
                        slot = tool_calls.setdefault(
                            tc.get("index", 0), {"id": "", "name": "", "arguments": ""}
                        )
                        if tc.get("id"):
                            slot["id"] = tc["id"]
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            slot["name"] += fn["name"]
                        if fn.get("arguments"):
                            slot["arguments"] += fn["arguments"]

            if not tool_calls:
                return

            calls = [tool_calls[i] for i in sorted(tool_calls)]
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": c["id"], "type": "function",
                     "function": {"name": c["name"], "arguments": c["arguments"]}}
                    for c in calls
                ],
            })
            for c in calls:
                func = FUNCTION_MAP.get(c["name"])
                try:
                    args = json.loads(c["arguments"] or "{}")
                    if not isinstance(args, dict):
                        args = {}
                    result = await func(args) if func else {"error": "unknown function"}
                except Exception as e:
                    result = {"error": str(e)}
                messages.append({
                    "role": "tool", "tool_call_id": c["id"], "content": json.dumps(result),
                })


async def connect_tts(language: str, speaker: str):
    tts = await websockets.connect(
        SARVAM_TTS_URL,
        additional_headers={"api-subscription-key": SARVAM_API_KEY},
    )
    await tts.send(json.dumps({
        "type": "config",
        "data": {
            "target_language_code": language,
            "speaker": speaker,
            "speech_sample_rate": "24000",
            "output_audio_codec": "linear16",
            "min_buffer_size": 30,
            "max_chunk_length": 250,
            "temperature": 0.7,  # bulbul:v3 expressiveness
            "pace": 0.95,
        },
    }))
    return tts


@app.websocket("/ws")
async def voice_agent(client_ws: WebSocket, llm_model: str = None):
    await client_ws.accept()

    active_llm_model = llm_model or LLM_MODEL

    if not SARVAM_API_KEY:
        await client_ws.send_json({"type": "Error", "description": "SARVAM_API_KEY not set"})
        await client_ws.close()
        return

    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    generation = [0]
    respond_task = None

    sarvam = AsyncSarvamAI(api_subscription_key=SARVAM_API_KEY)
    async with sarvam.speech_to_text_streaming.connect(
        model="saaras:v3",
        mode="transcribe",
        language_code=STT_LANGUAGE,
        sample_rate="16000",
        input_audio_codec="pcm_s16le",
        vad_signals="true",
        high_vad_sensitivity="true",  # 0.5s end-of-turn silence boundary
    ) as stt:

        async def respond(user_text: str, my_gen: int):
            try:
                await _respond(user_text, my_gen)
            except asyncio.CancelledError:
                raise
            except Exception:
                import traceback
                traceback.print_exc()

        async def _respond(user_text: str, my_gen: int):
            start_time = time.time()
            history.append({"role": "user", "content": user_text})
            messages = list(history)
            reply_parts = []

            detected_lang = detect_language_from_text(user_text)

            tts_task = asyncio.create_task(connect_tts(detected_lang, SARVAM_SPEAKER))
            llm = stream_llm(messages, active_llm_model)
            
            try:
                first = await llm.__anext__()
            except StopAsyncIteration:
                first = None
                
            tts = await tts_task
            try:
                async def forward_audio():
                    first_audio_sent = False
                    async for raw in tts:
                        if generation[0] != my_gen:
                            return
                        msg = json.loads(raw)
                        if msg.get("type") == "audio":
                            if not first_audio_sent:
                                latency_ms = int((time.time() - start_time) * 1000)
                                await client_ws.send_json({"type": "Latency", "latency_ms": latency_ms})
                                first_audio_sent = True
                            await client_ws.send_bytes(base64.b64decode(msg["data"]["audio"]))
                        elif msg.get("type") == "event" and msg["data"].get("event_type") == "final":
                            return
                        elif msg.get("type") == "error":
                            await client_ws.send_json({
                                "type": "Error", "description": msg["data"].get("message", ""),
                            })
                            return

                audio_task = asyncio.create_task(forward_audio())

                buffer = ""
                sent_first = False

                async def maybe_send(buf, force=False):
                    # full sentences only: comma-level fragments make the TTS
                    # prosody flat and robotic
                    nonlocal sent_first
                    boundary = buf.rstrip().endswith((".", "!", "?", "।"))
                    min_len = 1 if not sent_first else 40
                    if force or (boundary and len(buf) >= min_len):
                        if buf.strip():
                            await tts.send(json.dumps({"type": "text", "data": {"text": buf}}))
                            sent_first = True
                        return ""
                    return buf

                async def consume(delta):
                    nonlocal buffer
                    reply_parts.append(delta)
                    buffer += delta
                    buffer = await maybe_send(buffer)

                if first is not None:
                    await consume(first)
                    async for delta in llm:
                        if generation[0] != my_gen:
                            break
                        await consume(delta)

                if generation[0] == my_gen:
                    await maybe_send(buffer, force=True)
                    await tts.send(json.dumps({"type": "flush"}))
                    await audio_task
                else:
                    audio_task.cancel()
            finally:
                await tts.close()

            reply = "".join(reply_parts)
            if generation[0] == my_gen and reply:
                history.append({"role": "assistant", "content": reply})
                await client_ws.send_json({
                    "type": "ConversationText", "role": "assistant", "content": reply,
                })
                await client_ws.send_json({"type": "AgentAudioDone"})

        async def browser_to_stt():
            while True:
                message = await client_ws.receive()
                if message.get("type") == "websocket.disconnect":
                    break
                if message.get("bytes") is not None:
                    await stt.transcribe(
                        audio=base64.b64encode(message["bytes"]).decode(),
                        encoding="audio/wav",  # SDK literal; raw PCM is set via input_audio_codec
                        sample_rate=16000,
                    )

        async def stt_loop():
            nonlocal respond_task
            while True:
                resp = await stt.recv()
                rtype = getattr(resp, "type", None)
                data = getattr(resp, "data", None)
                if rtype == "events":
                    signal = getattr(data, "signal_type", "") or ""
                    if "START" in signal and respond_task and not respond_task.done():
                        generation[0] += 1
                        respond_task.cancel()
                        await client_ws.send_json({"type": "UserStartedSpeaking"})
                    continue
                transcript = (getattr(data, "transcript", "") or "").strip()
                if not transcript:
                    continue
                await client_ws.send_json({
                    "type": "ConversationText", "role": "user", "content": transcript,
                })
                if respond_task and not respond_task.done():
                    generation[0] += 1
                    respond_task.cancel()
                generation[0] += 1
                respond_task = asyncio.create_task(respond(transcript, generation[0]))

        tasks = [
            asyncio.create_task(browser_to_stt()),
            asyncio.create_task(stt_loop()),
        ]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        except WebSocketDisconnect:
            pass
        finally:
            for task in tasks:
                task.cancel()
            if respond_task:
                respond_task.cancel()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
