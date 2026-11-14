import { useEffect, useState } from 'react';
import { LLM_MODELS, MODEL_INFO } from '../lib/config.js';
import { formatDuration } from '../lib/format.js';
import { MicIcon, PhoneOffIcon } from './icons.jsx';

const PHASE_TEXT = {
  listening: { title: 'Listening', detail: 'Go ahead and speak.' },
  thinking: { title: 'Thinking', detail: 'Working on a reply…' },
  speaking: { title: 'Speaking', detail: 'Talk over the agent any time to interrupt.' },
};

function useElapsed(startedAt) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!startedAt) return undefined;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [startedAt]);
  return startedAt ? Math.max(0, (now - startedAt) / 1000) : 0;
}

function ModelPicker({ value, onChange, disabled }) {
  return (
    <fieldset className="model-picker" disabled={disabled}>
      <legend className="field-label">Language model</legend>
      <div className="segmented">
        {LLM_MODELS.map((model) => (
          <label key={model} className="segment">
            <input
              type="radio"
              name="llm-model"
              value={model}
              checked={value === model}
              onChange={() => onChange(model)}
            />
            <span className="segment-body">
              <span className="segment-title">{MODEL_INFO[model]?.label ?? model}</span>
              <span className="segment-hint">{MODEL_INFO[model]?.hint}</span>
            </span>
          </label>
        ))}
      </div>
      {disabled && <p className="field-help">End the call to switch models.</p>}
    </fieldset>
  );
}

export default function CallPanel({
  status,
  phase,
  latency,
  startedAt,
  llmModel,
  onModelChange,
  onStart,
  onEnd,
}) {
  const elapsed = useElapsed(startedAt);
  const visualState = status === 'active' ? phase : status;

  let title = 'Ready when you are';
  let detail = 'Start a call and talk in Hindi, English, Hinglish or another Indian language.';
  if (status === 'connecting') {
    title = 'Connecting…';
    detail = 'Allow microphone access if your browser asks.';
  } else if (status === 'active') {
    ({ title, detail } = PHASE_TEXT[phase]);
  }

  return (
    <section className="card call-panel" aria-label="Call">
      <div className={`orb orb-${visualState}`} aria-hidden="true">
        <span className="orb-ring" />
        <span className="orb-ring orb-ring-2" />
        <span className="orb-core">
          <MicIcon width={44} height={44} strokeWidth={1.75} />
        </span>
      </div>

      <div className="call-status" role="status" aria-live="polite">
        <p className="call-title">{title}</p>
        <p className="call-detail">{detail}</p>
      </div>

      <div className="call-meta" aria-label="Call details">
        {status === 'active' && (
          <span className="chip">
            <span className="chip-dot chip-dot-live" aria-hidden="true" />
            <span className="visually-hidden">Call time </span>
            <span className="tabular">{formatDuration(elapsed)}</span>
          </span>
        )}
        {latency !== null && (
          <span
            className="chip chip-ok"
            title="Time from the end of your speech to the first audio"
          >
            First audio in <span className="tabular">{latency} ms</span>
          </span>
        )}
      </div>

      {status === 'idle' ? (
        <button type="button" className="button button-primary button-lg" onClick={onStart}>
          <MicIcon />
          Start call
        </button>
      ) : (
        <button type="button" className="button button-danger button-lg" onClick={onEnd}>
          <PhoneOffIcon />
          {status === 'connecting' ? 'Cancel' : 'End call'}
        </button>
      )}

      <ModelPicker value={llmModel} onChange={onModelChange} disabled={status !== 'idle'} />

      <p className="call-footnote">
        Headphones give the cleanest results. Audio is streamed to the backend only while a call is
        active.
      </p>
    </section>
  );
}
