import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AGENT_SAMPLE_RATE,
  MIC_SAMPLE_RATE,
  floatTo16BitPCM,
  pcm16ToFloat32,
} from '../lib/audio.js';
import { defaultWsUrl } from '../lib/config.js';
// Served from public/ as a real file (not inlined) so every browser can load it.
const micWorkletUrl = `${import.meta.env.BASE_URL}mic-worklet.js`;
import { BACKEND_UNREACHABLE, UNSUPPORTED_BROWSER, backendError, micError } from '../lib/errors.js';

/**
 * Owns one voice call: microphone capture, the backend websocket and agent
 * audio playback.
 *
 * `status` is idle | connecting | active. While active, `phase` says what
 * the conversation is doing: listening | thinking | speaking.
 */
export function useVoiceCall() {
  const [status, setStatus] = useState('idle');
  const [phase, setPhase] = useState('listening');
  const [latency, setLatency] = useState(null);
  const [error, setError] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [startedAt, setStartedAt] = useState(null);

  const wsRef = useRef(null);
  const micCtxRef = useRef(null);
  const playCtxRef = useRef(null);
  const streamRef = useRef(null);
  const processorRef = useRef(null);
  const nextPlayTimeRef = useRef(0);
  const playDestRef = useRef(null);
  const audioElRef = useRef(null);
  const sourcesRef = useRef(new Set());

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
    if (processorRef.current?.port) processorRef.current.port.onmessage = null;
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
    setPhase('listening');
    setLatency(null);
    setStartedAt(null);
  }, []);

  useEffect(() => endCall, [endCall]);

  const startAudio = async (ws, stream) => {
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

    const sendFrame = (samples) => {
      if (ws.readyState !== WebSocket.OPEN) return;
      ws.send(floatTo16BitPCM(samples).buffer);
    };

    const source = micCtx.createMediaStreamSource(stream);
    let processor;
    if (micCtx.audioWorklet) {
      await micCtx.audioWorklet.addModule(micWorkletUrl);
      processor = new AudioWorkletNode(micCtx, 'mic-capture');
      processor.port.onmessage = (e) => sendFrame(e.data);
    } else {
      // Fallback for browsers without AudioWorklet support.
      processor = micCtx.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (e) => sendFrame(e.inputBuffer.getChannelData(0));
    }
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
        setPhase('listening');
        setLatency(null);
        break;
      case 'AgentAudioDone':
        setPhase('listening');
        break;
      case 'Latency':
        setPhase('speaking');
        setLatency(msg.latency_ms);
        break;
      case 'ConversationText':
        setTranscript((prev) => [...prev, { role: msg.role, content: msg.content }]);
        if (msg.role === 'user') setPhase('thinking');
        break;
      case 'Error':
        setError(backendError(msg.description));
        break;
      default:
        break;
    }
  };

  const startCall = async (llmModel) => {
    setError(null);
    setTranscript([]);
    setLatency(null);

    if (!navigator.mediaDevices?.getUserMedia || typeof AudioContext === 'undefined') {
      setError(UNSUPPORTED_BROWSER);
      return;
    }

    setStatus('connecting');
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
    } catch (err) {
      setError(micError(err));
      setStatus('idle');
      return;
    }
    streamRef.current = stream;

    let opened = false;
    const ws = new WebSocket(defaultWsUrl(llmModel));
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;

    ws.onopen = async () => {
      opened = true;
      try {
        await startAudio(ws, stream);
        if (wsRef.current !== ws) return; // call ended while audio was starting
        setPhase('listening');
        setStartedAt(Date.now());
        setStatus('active');
      } catch (err) {
        // Ignore failures caused by the call ending (e.g. the backend
        // rejected it) while audio was still starting up.
        if (wsRef.current !== ws) return;
        setError(micError(err));
        endCall();
      }
    };
    ws.onmessage = handleMessage;
    ws.onerror = () => {
      if (!opened) setError(BACKEND_UNREACHABLE);
    };
    ws.onclose = () => endCall();
  };

  return {
    status,
    phase,
    latency,
    error,
    transcript,
    startedAt,
    startCall,
    endCall,
    dismissError: () => setError(null),
  };
}
