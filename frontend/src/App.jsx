import { useRef, useState } from 'react';

const WS_URL = 'ws://localhost:8004/ws';
const MIC_SAMPLE_RATE = 16000;
const AGENT_SAMPLE_RATE = 24000;

export default function App() {
  const [status, setStatus] = useState('idle'); // idle | connecting | active
  const [agentState, setAgentState] = useState('');
  const [llmModel, setLlmModel] = useState('sarvam-30b');
  const [latency, setLatency] = useState(null);

  const wsRef = useRef(null);
  const micCtxRef = useRef(null);
  const playCtxRef = useRef(null);
  const streamRef = useRef(null);
  const nextPlayTimeRef = useRef(0);
  const playDestRef = useRef(null);
  const audioElRef = useRef(null);

  const playAudioChunk = (arrayBuffer) => {
    const ctx = playCtxRef.current;
    if (!ctx) return;
    const int16 = new Int16Array(arrayBuffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 32768;

    const buffer = ctx.createBuffer(1, float32.length, AGENT_SAMPLE_RATE);
    buffer.getChannelData(0).set(float32);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(playDestRef.current);

    const startAt = Math.max(ctx.currentTime, nextPlayTimeRef.current);
    source.start(startAt);
    nextPlayTimeRef.current = startAt + buffer.duration;
  };

  const startCall = async () => {
    setStatus('connecting');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;

      const wsUrl = `ws://localhost:8004/ws?llm_model=${encodeURIComponent(llmModel)}`;
      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      ws.onopen = () => {
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
        audioEl.play();
        audioElRef.current = audioEl;

        const source = micCtx.createMediaStreamSource(stream);
        const processor = micCtx.createScriptProcessor(4096, 1, 1);
        processor.onaudioprocess = (e) => {
          if (ws.readyState !== WebSocket.OPEN) return;
          const input = e.inputBuffer.getChannelData(0);
          const int16 = new Int16Array(input.length);
          for (let i = 0; i < input.length; i++) {
            const s = Math.max(-1, Math.min(1, input[i]));
            int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
          }
          ws.send(int16.buffer);
        };
        source.connect(processor);
        processor.connect(micCtx.destination);
        setStatus('active');
      };

      ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
          playAudioChunk(event.data);
          return;
        }
        const msg = JSON.parse(event.data);
        if (msg.type === 'UserStartedSpeaking') {
          // Barge-in: stop queued agent audio
          nextPlayTimeRef.current = 0;
          setAgentState('Listening...');
          setLatency(null);
        } else if (msg.type === 'AgentStartedSpeaking' || msg.type === 'AgentAudioDone') {
          setAgentState(msg.type === 'AgentAudioDone' ? '' : 'Agent speaking...');
        } else if (msg.type === 'Latency') {
          setLatency(msg.latency_ms);
        } else if (msg.type === 'ConversationText') {
          setAgentState(`${msg.role}: ${msg.content}`);
        } else if (msg.type === 'Error') {
          console.error('Agent error:', msg);
        }
      };

      ws.onclose = () => endCall();
      ws.onerror = () => endCall();
    } catch (err) {
      console.error(err);
      setStatus('idle');
    }
  };

  const endCall = () => {
    wsRef.current?.close();
    wsRef.current = null;
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
  };

  return (
    <div style={styles.page}>
      <h1>Sarvam Voice Agent</h1>
      <p style={styles.status}>
        {status === 'idle' && 'Ready to start a call'}
        {status === 'connecting' && 'Connecting...'}
        {status === 'active' && (
          <>
            {agentState || 'Call active — speak now'}
            {latency !== null && <span style={{ color: '#059669', marginLeft: '0.5rem' }}>(Latency: {latency}ms)</span>}
          </>
        )}
      </p>
      {status === 'idle' ? (
        <>
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
            <label style={{ display: 'flex', flexDirection: 'column', fontSize: '0.9rem', alignItems: 'center' }}>
              <span style={{ marginBottom: '0.25rem', fontWeight: 500 }}>LLM Model</span>
              <select
                value={llmModel}
                onChange={(e) => setLlmModel(e.target.value)}
                style={styles.select}
              >
                <option value="sarvam-30b">sarvam-30b</option>
                <option value="sarvam-105b">sarvam-105b</option>
              </select>
            </label>
          </div>
          <button style={{ ...styles.button, background: '#16a34a' }} onClick={startCall}>
            Start Call
          </button>
        </>
      ) : (
        <button style={{ ...styles.button, background: '#dc2626' }} onClick={endCall}>
          End Call
        </button>
      )}
    </div>
  );
}

const styles = {
  page: {
    fontFamily: 'system-ui, sans-serif',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    gap: '1rem',
  },
  status: { color: '#555', minHeight: '1.5em' },
  button: {
    color: 'white',
    border: 'none',
    borderRadius: '9999px',
    padding: '1rem 2.5rem',
    fontSize: '1.1rem',
    cursor: 'pointer',
  },
  select: {
    padding: '0.5rem',
    borderRadius: '4px',
    border: '1px solid #ccc',
    fontSize: '1rem',
    minWidth: '150px',
  },
};
