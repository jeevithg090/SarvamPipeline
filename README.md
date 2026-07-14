# Sarvam Voice Agent

Fully Indian-language voice agent, all Sarvam APIs, everything streaming:

- **STT** — Saaras v3 streaming (auto-detects 24 Indic languages, server-side VAD)
- **LLM** — Sarvam-30B, streaming, `reasoning_effort` disabled for low latency
- **TTS** — Bulbul v3 streaming (37 voices, 11 languages)

LLM tokens stream straight into the TTS websocket phrase-by-phrase, and the TTS
connection opens in parallel with the LLM request, so the agent starts speaking
~0.6–1.2s after you stop talking.

## Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # add your SARVAM_API_KEY
python main.py            # runs on :8004
```

`.env` knobs: `SARVAM_SPEAKER` (voice), `SARVAM_LANGUAGE` (TTS language),
`STT_LANGUAGE` (`unknown` = auto-detect), `LLM_MODEL` (`sarvam-30b` / `sarvam-105b`).

## Frontend

```bash
cd frontend
npm install
npm run dev               # runs on :5177
```

Open http://localhost:5177 and click **Start Call**. Speak in Hindi, English,
Hinglish, or any supported Indian language.

## Get a key

Sarvam dashboard: https://dashboard.sarvam.ai — key goes in `backend/.env`.
