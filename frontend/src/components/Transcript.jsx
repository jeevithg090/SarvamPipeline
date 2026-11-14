import { useEffect, useRef, useState } from 'react';
import { transcriptToText } from '../lib/format.js';
import { ChatIcon, CheckIcon, CopyIcon } from './icons.jsx';

const EXAMPLES = [
  'नमस्ते, आज मौसम कैसा है?',
  'What time is it right now?',
  'Bengaluru mein weather kaisa hai?',
];

function EmptyState({ active }) {
  return (
    <div className="empty-state">
      <span className="empty-icon" aria-hidden="true">
        <ChatIcon width={28} height={28} />
      </span>
      <p className="empty-title">{active ? 'Say something to begin' : 'No conversation yet'}</p>
      <p className="empty-text">
        Both sides of the conversation appear here as you talk. Try asking:
      </p>
      <ul className="examples">
        {EXAMPLES.map((text) => (
          <li key={text} lang={/[ऀ-ॿ]/.test(text) ? 'hi' : undefined}>
            “{text}”
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Transcript({ turns, active }) {
  const listRef = useRef(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns]);

  useEffect(() => {
    if (!copied) return undefined;
    const id = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(id);
  }, [copied]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(transcriptToText(turns));
      setCopied(true);
    } catch {
      // clipboard blocked; nothing useful to show
    }
  };

  const canCopy = turns.length > 0 && Boolean(navigator.clipboard);

  return (
    <section className="card transcript" aria-labelledby="transcript-title">
      <div className="card-header">
        <h2 id="transcript-title" className="card-title">
          Transcript
          {turns.length > 0 && <span className="count">{turns.length}</span>}
        </h2>
        {canCopy && (
          <button type="button" className="button button-ghost button-sm" onClick={copy}>
            {copied ? <CheckIcon width={16} height={16} /> : <CopyIcon width={16} height={16} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        )}
      </div>
      <span className="visually-hidden" role="status">
        {copied ? 'Transcript copied to clipboard' : ''}
      </span>

      {turns.length === 0 ? (
        <EmptyState active={active} />
      ) : (
        <ol className="turns" ref={listRef} tabIndex={0} aria-label="Conversation messages">
          {turns.map((turn, i) => (
            <li key={i} className={`turn turn-${turn.role === 'user' ? 'user' : 'agent'}`}>
              <span className="turn-role">{turn.role === 'user' ? 'You' : 'Agent'}</span>
              <p className="turn-text">{turn.content}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
