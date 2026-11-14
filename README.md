# Sarvam Voice Agent

A real-time, fully streaming voice assistant for Indian languages, built entirely on Sarvam AI's speech-to-text, LLM and text-to-speech APIs.

Open the web app, click **Start Call** and talk in Hindi, English, Hinglish or another supported Indian language. The agent transcribes you as you speak, notices when you stop, and answers out loud in the same language. It starts speaking while the rest of the reply is still being generated.

## Features

- **Streaming speech-to-text** with Saaras v3. The language is detected automatically, and server-side voice-activity detection finds the end of each turn (about 0.5 s of silence).
- **Streaming LLM replies** from `sarvam-30b` or `sarvam-105b`, picked in the UI. Reasoning is turned off to keep latency low.
- **Streaming text-to-speech** with Bulbul v3. The voice language follows the user: it uses the language the STT reports, or else the script of the transcript (Devanagari, Tamil, Bengali and so on).
- **Overlapped pipeline:** the TTS websocket opens while the LLM request is in flight, and LLM tokens go to TTS one sentence at a time.
- **Barge-in:** if you start talking while the agent is speaking, the current reply is cancelled and its queued audio is stopped.
- **Function calling:** OpenAI-style tool calls are run on the server and their results are passed back to the LLM. Two demo tools are included (`get_current_time`, `get_weather`; the weather tool returns mock data).
- **Latency readout:** the UI shows the time from the end of your speech to the agent's first audio.
- **Live transcript** of both sides of the conversation, plus clear error messages (microphone denied, backend not reachable, API errors).

## Tech stack

| Layer    | Technology                                                                  |
| -------- | --------------------------------------------------------------------------- |
| Backend  | Python 3.10+, FastAPI, Uvicorn, `httpx`, `websockets`, `sarvamai` SDK       |
| Frontend | React 18, Vite 6, Web Audio API                                             |
| AI       | Sarvam Saaras v3 (STT), Sarvam-30B / 105B (LLM), Bulbul v3 (TTS)            |
| Tooling  | pytest, Ruff (backend); Vitest, ESLint, Prettier (frontend); GitHub Actions |

## Architecture

```
Browser (React)                     Backend (FastAPI, /ws)                   Sarvam AI
───────────────                     ──────────────────────                   ─────────
mic ─► 16 kHz PCM frames ─────────► browser_to_stt ────────────────────────► Saaras v3 STT (websocket)
                                                                                 │ VAD events + transcripts
                                    stt_loop ◄───────────────────────────────────┘
                                      │ transcript (barge-in cancels the reply in progress)
                                      ▼
                                    respond ── chat completions (SSE) ──────► Sarvam LLM
                                      │          └─ runs tool calls, then continues
                                      │ text deltas ─► SentenceChunker
                                      ▼
                                    TTS websocket (opened in parallel) ─────► Bulbul v3 TTS
speaker ◄─ 24 kHz PCM frames ◄───── forward_audio ◄─────────────────────────────┘
transcript, latency ◄─ JSON events
```

**Websocket protocol (`/ws?llm_model=<model>`)**

- Browser to server: binary frames of 16 kHz mono PCM s16le microphone audio.
- Server to browser: binary frames of 24 kHz mono PCM s16le agent audio, plus JSON events:
  `ConversationText` (`role`, `content`), `UserStartedSpeaking`, `Latency` (`latency_ms`), `AgentAudioDone`, `Error` (`description`).

## Prerequisites

- Python 3.10 or newer
- Node.js 20 or newer
- A Sarvam API subscription key from the [Sarvam dashboard](https://dashboard.sarvam.ai)
- A Chromium-based browser is recommended. The page records at 16 kHz using a dedicated `AudioContext`, and some browsers (notably Firefox) refuse to connect a microphone stream to a context running at a different sample rate.

## Setup

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # requirements-dev.txt adds pytest + ruff
cp .env.example .env                     # then set SARVAM_API_KEY
python main.py                           # serves on http://127.0.0.1:8004
```

### Frontend

```bash
cd frontend
npm install
npm run dev                              # serves on http://localhost:5177
```

Open http://localhost:5177, allow microphone access and click **Start Call**.

## Environment variables

Backend (`backend/.env`, see [`backend/.env.example`](backend/.env.example)):

| Variable          | Default                                       | Description                                                                               |
| ----------------- | --------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `SARVAM_API_KEY`  | none (required)                               | Sarvam API subscription key                                                               |
| `SARVAM_LANGUAGE` | `hi-IN`                                       | TTS language used when the reply language can't be detected                               |
| `SARVAM_SPEAKER`  | `shubh`                                       | Bulbul v3 voice                                                                           |
| `STT_LANGUAGE`    | `unknown`                                     | STT language code; `unknown` means auto-detect                                            |
| `LLM_MODEL`       | `sarvam-30b`                                  | Default model when the client doesn't choose one (`sarvam-30b` or `sarvam-105b`)          |
| `ALLOWED_ORIGINS` | `http://localhost:5177,http://127.0.0.1:5177` | Comma-separated browser origins allowed for CORS and the websocket; `*` allows any origin |
| `HOST`            | `127.0.0.1`                                   | Bind address for `python main.py`                                                         |
| `PORT`            | `8004`                                        | Port for `python main.py`                                                                 |

Frontend (optional, `frontend/.env`):

| Variable      | Default                       | Description           |
| ------------- | ----------------------------- | --------------------- |
| `VITE_WS_URL` | `ws(s)://<page host>:8004/ws` | Backend websocket URL |

## Testing and linting

```bash
# Backend
cd backend
pip install -r requirements-dev.txt
ruff check . && ruff format --check .
pytest

# Frontend
cd frontend
npm run lint
npm run format:check
npm test
npm run build
```

The backend tests cover language detection, sentence chunking, SSE parsing, tool-call assembly, the function-calling loop (using a mocked HTTP transport), websocket validation, and one full conversational turn through `/ws` with the Sarvam services faked. None of the tests call the real Sarvam APIs.

GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs these checks on every push to `main` and on every pull request. It also builds the backend Docker image.

## Deployment

**Backend.** A Dockerfile is included:

```bash
cd backend
docker build -t sarvam-voice-backend .
docker run -p 8004:8004 \
  -e SARVAM_API_KEY=... \
  -e ALLOWED_ORIGINS=https://your-frontend.example \
  sarvam-voice-backend
```

**Frontend.** `npm run build` writes a static site to `frontend/dist/` that any static host can serve. Set `VITE_WS_URL` at build time to point the site at the backend, for example `wss://api.example.com/ws`.

Production notes:

- Browsers only allow microphone access on secure origins (HTTPS or `localhost`). Serve the frontend over HTTPS and the backend over `wss://`, for example behind a TLS-terminating reverse proxy that supports websockets.
- Set `ALLOWED_ORIGINS` to your frontend's origin. The backend uses your Sarvam key for every call, so any origin you allow can spend your credits.
- The backend has no user authentication. Put it behind your own auth or rate limiting before exposing it publicly.

## Project structure

```
.
├── backend/
│   ├── main.py              # FastAPI app: /health, /ws call pipeline (CallSession)
│   ├── config.py            # Settings from environment / .env
│   ├── llm.py               # Streaming Sarvam chat client + function-calling loop
│   ├── tts.py               # Bulbul v3 websocket helpers, SentenceChunker
│   ├── language.py          # TTS language selection (STT result / script detection)
│   ├── agent_functions.py   # Tool definitions and implementations
│   ├── tests/               # pytest suite
│   ├── Dockerfile
│   ├── pyproject.toml       # Ruff + pytest config
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── index.html
│   ├── public/favicon.svg
│   ├── src/
│   │   ├── App.jsx          # Call UI, mic capture, audio playback, transcript
│   │   ├── lib/audio.js     # PCM conversion helpers
│   │   ├── lib/config.js    # Backend URL + model list
│   │   └── styles.css
│   ├── eslint.config.js
│   └── vite.config.js
└── .github/workflows/ci.yml
```

## Adding tools

Tools live in [`backend/agent_functions.py`](backend/agent_functions.py). To add one, write an async function that takes an `arguments` dict and returns a JSON-serialisable dict. Then add its JSON-schema definition to `FUNCTION_DEFINITIONS` and register it in `FUNCTION_MAP`.
