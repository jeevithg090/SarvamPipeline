import { useEffect, useState } from 'react';
import CallPanel from './components/CallPanel.jsx';
import ErrorBanner from './components/ErrorBanner.jsx';
import Header from './components/Header.jsx';
import Transcript from './components/Transcript.jsx';
import { useBackendHealth } from './hooks/useBackendHealth.js';
import { useTheme } from './hooks/useTheme.js';
import { useVoiceCall } from './hooks/useVoiceCall.js';
import { LLM_MODELS } from './lib/config.js';

const BASE_TITLE = 'Sarvam Voice Agent';

const LANGUAGES = [
  'Hindi',
  'English',
  'Bengali',
  'Gujarati',
  'Kannada',
  'Malayalam',
  'Marathi',
  'Odia',
  'Punjabi',
  'Tamil',
  'Telugu',
];

export default function App() {
  const [theme, setTheme] = useTheme();
  const [llmModel, setLlmModel] = useState(LLM_MODELS[0]);
  const health = useBackendHealth();
  const call = useVoiceCall();

  useEffect(() => {
    document.title = call.status === 'active' ? `● On call · ${BASE_TITLE}` : BASE_TITLE;
  }, [call.status]);

  return (
    <div className="app">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <Header
        theme={theme}
        onThemeChange={setTheme}
        health={health.state}
        onRecheck={health.recheck}
      />

      <main id="main" className="layout" tabIndex={-1}>
        <h1 className="visually-hidden">Sarvam Voice Agent</h1>
        <div className="layout-alerts">
          <ErrorBanner error={call.error} onDismiss={call.dismissError} />
          {!call.error && call.status === 'idle' && health.state === 'offline' && (
            <p className="notice">
              The backend isn’t answering at the moment. Start it with <code>python main.py</code>{' '}
              in <code>backend/</code>, then press the refresh button above.
            </p>
          )}
          {!call.error && call.status === 'idle' && health.state === 'no-key' && (
            <p className="notice">
              The backend is running but has no <code>SARVAM_API_KEY</code>. Add it to{' '}
              <code>backend/.env</code> and restart the backend.
            </p>
          )}
        </div>

        <CallPanel
          status={call.status}
          phase={call.phase}
          latency={call.latency}
          startedAt={call.startedAt}
          llmModel={llmModel}
          onModelChange={setLlmModel}
          onStart={() => call.startCall(llmModel)}
          onEnd={call.endCall}
        />
        <Transcript turns={call.transcript} active={call.status === 'active'} />
      </main>

      <footer className="site-footer">
        <p>
          <span className="footer-label">Speaks:</span> {LANGUAGES.join(' · ')}
        </p>
        <p>
          Speech recognition, language model and voice by{' '}
          <a href="https://www.sarvam.ai" target="_blank" rel="noreferrer">
            Sarvam AI
          </a>
          .
        </p>
      </footer>
    </div>
  );
}
