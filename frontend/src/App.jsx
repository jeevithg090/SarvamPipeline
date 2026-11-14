import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AGENT_SAMPLE_RATE,
  MIC_SAMPLE_RATE,
  floatTo16BitPCM,
  pcm16ToFloat32,
} from './lib/audio.js';
import { LLM_MODELS, defaultWsUrl } from './lib/config.js';

const STATUS_TEXT = {
  idle: 'Ready to start a call',
  connecting: 'Connecting…',
  active: 'Call active — speak now',
};

function micErrorMessage(err) {
  if (err?.name === 'NotAllowedError') return 'Microphone access was denied.';
  if (err?.name === 'NotFoundError') return 'No microphone was found.';
  return `Could not start audio: ${err?.message || err}`;
}

export default function App() {
  const [status, setStatus] = useState('idle'); // idle | connecting | active
  const [agentState, setAgentState] = useState('');
  const [llmModel, setLlmModel] = useState(LLM_MODELS[0]);
  const [latency, setLatency] = useState(null);
  const [error, setError] = useState('');
  const [transcript, setTranscript] = useState([]);

  const wsRef = useRef(null);
  const micCtxRef = useRef(null);
  const playCtxRef = useRef(null);
  const streamRef = useRef(null);
  const processorRef = useRef(null);
  const nextPlayTimeRef = useRef(0);
  const playDestRef = useRef(null);
  const audioElRef = useRef(null);
  const sourcesRef = useRef(new Set());
  const transcriptEndRef = useRef(null);

  const stopPlayback = () => {
    sourcesRef.current.forEach((source) => {
      try {
        source.stop();
      } catch {
        // already stopped
      }
    });
    sourcesRef.current.clear();
    nextPlayTimeRef.current = 0;
  };

  const playAudioChunk = (arrayBuffer) => {
    const ctx = playCtxRef.current;
    if (!ctx || !playDestRef.current) return;
    const samples = pcm16ToFloat32(arrayBuffer);
    if (samples.length === 0) return;

    const buffer = ctx.createBuffer(1, samples.length, AGENT_SAMPLE_RATE);
    buffer.getChannelData(0).set(samples);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(playDestRef.current);
    source.onended = () => sourcesRef.current.delete(source);
    sourcesRef.current.add(source);

    const startAt = Math.max(ctx.currentTime, nextPlayTimeRef.current);
    source.start(startAt);
    nextPlayTimeRef.current = startAt + buffer.duration;
  };

  const endCall = useCallback(() => {
    const ws = wsRef.current;
    if (ws) {
      ws.onopen = ws.onmessage = ws.onclose = ws.onerror = null;
      ws.close();
    }
    wsRef.current = null;
    stopPlayback();
    processorRef.current?.disconnect();
    processorRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    micCtxRef.current?.close();
    micCtxRef.current = null;
    playCtxRef.current?.close();
    playCtxRef.current = null;
    audioElRef.current?.pause();
    audioElRef.current = null;
    playDestRef.current = null;
    setStatus('idle');
    setAgentState('');
    setLatency(null);
  }, []);

  useEffect(() => endCall, [endCall]);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView?.({ block: 'nearest' });
  }, [transcript]);

  const startAudio = (ws, stream) => {
    const micCtx = new AudioContext({ sampleRate: MIC_SAMPLE_RATE });
    micCtxRef.current = micCtx;
    const playCtx = new AudioContext({ sampleRate: AGENT_SAMPLE_RATE });
    playCtxRef.current = playCtx;
    nextPlayTimeRef.current = 0;

    // Route agent audio through an <audio> element so the browser's
    // echo canceller subtracts it from the mic.
    const playDest = playCtx.createMediaStreamDestination();
    playDestRef.current = playDest;
    const audioEl = new Audio();
    audioEl.srcObject = playDest.stream;
    audioEl.play().catch((err) => console.warn('Audio playback blocked:', err));
    audioElRef.current = audioEl;

    const source = micCtx.createMediaStreamSource(stream);
    const processor = micCtx.createScriptProcessor(4096, 1, 1);
    processor.onaudioprocess = (e) => {
      if (ws.readyState !== WebSocket.OPEN) return;
      ws.send(floatTo16BitPCM(e.inputBuffer.getChannelData(0)).buffer);
    };
    source.connect(processor);
    processor.connect(micCtx.destination);
    processorRef.current = processor;
  };

  const handleMessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
      playAudioChunk(event.data);
      return;
    }
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch {
      return;
    }
    switch (msg.type) {
      case 'UserStartedSpeaking': // barge-in: drop queued agent audio
        stopPlayback();
        setAgentState('Listening…');
        setLatency(null);
        break;
      case 'AgentAudioDone':
        setAgentState('');
        break;
      case 'Latency':
        setAgentState('Agent speaking…');
        setLatency(msg.latency_ms);
        break;
      case 'ConversationText':
        setTranscript((prev) => [...prev, { role: msg.role, content: msg.content }]);
        if (msg.role === 'user') setAgentState('Thinking…');
        break;
      case 'Error':
        setError(msg.description || 'Something went wrong.');
        break;
      default:
        break;
    }
  };

  const startCall = async () => {
    setError('');
    setTranscript([]);
    setStatus('connecting');
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
    } catch (err) {
      setError(micErrorMessage(err));
      setStatus('idle');
      return;
    }
    streamRef.current = stream;

    let opened = false;
    const ws = new WebSocket(defaultWsUrl(llmModel));
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;

    ws.onopen = () => {
      opened = true;
      try {
        startAudio(ws, stream);
        setStatus('active');
      } catch (err) {
        setError(micErrorMessage(err));
        endCall();
      }
    };
    ws.onmessage = handleMessage;
    ws.onerror = () => {
      if (!opened) setError('Could not reach the voice agent backend. Is it running?');
    };
    ws.onclose = () => endCall();
  };

  const busy = status !== 'idle';

  return (
    <main className="page">
      <header className="header">
        <h1>Sarvam Voice Agent</h1>
        <p className="subtitle">Talk in Hindi, English, Hinglish or any Indian language.</p>
      </header>

      <p className="status" role="status" aria-live="polite">
        {status === 'active' ? agentState || STATUS_TEXT.active : STATUS_TEXT[status]}
        {latency !== null && <span className="latency">First audio in {latency} ms</span>}
      </p>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}

      <div className="controls">
        <label className="field">
          <span>LLM model</span>
          <select value={llmModel} onChange={(e) => setLlmModel(e.target.value)} disabled={busy}>
            {LLM_MODELS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>

        {busy ? (
          <button type="button" className="button button-end" onClick={endCall}>
            End Call
          </button>
        ) : (
          <button type="button" className="button button-start" onClick={startCall}>
            Start Call
          </button>
        )}
      </div>

      {transcript.length > 0 && (
        <section className="transcript" aria-label="Conversation transcript">
          <ol>
            {transcript.map((turn, i) => (
              <li key={i} className={`turn turn-${turn.role}`}>
                <span className="turn-role">{turn.role === 'user' ? 'You' : 'Agent'}</span>
                <span className="turn-text">{turn.content}</span>
              </li>
            ))}
          </ol>
          <div ref={transcriptEndRef} />
        </section>
      )}
    </main>
  );
}
