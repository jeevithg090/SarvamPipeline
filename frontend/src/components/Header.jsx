import { LogoMark, MonitorIcon, MoonIcon, RefreshIcon, SunIcon } from './icons.jsx';
import { THEMES } from '../hooks/useTheme.js';

const THEME_META = {
  system: { label: 'System', Icon: MonitorIcon },
  light: { label: 'Light', Icon: SunIcon },
  dark: { label: 'Dark', Icon: MoonIcon },
};

const HEALTH_META = {
  checking: { label: 'Checking backend…', tone: 'neutral' },
  ready: { label: 'Backend ready', tone: 'ok' },
  'no-key': { label: 'API key missing', tone: 'warn' },
  offline: { label: 'Backend offline', tone: 'bad' },
};

function BackendStatus({ health, onRecheck }) {
  const meta = HEALTH_META[health];
  const canRetry = health === 'offline' || health === 'no-key';
  return (
    <div className={`pill pill-${meta.tone}`} title={meta.label}>
      <span className="pill-dot" aria-hidden="true" />
      <span className="pill-label">{meta.label}</span>
      {canRetry && (
        <button
          type="button"
          className="icon-button icon-button-sm"
          onClick={onRecheck}
          aria-label="Check backend again"
          title="Check again"
        >
          <RefreshIcon width={16} height={16} />
        </button>
      )}
    </div>
  );
}

export default function Header({ theme, onThemeChange, health, onRecheck }) {
  const next = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length];
  const { label, Icon } = THEME_META[theme];
  return (
    <header className="site-header">
      <div className="site-header-inner">
        <a className="brand" href="/" aria-label="Sarvam Voice Agent home">
          <LogoMark />
          <span className="brand-name">Sarvam Voice Agent</span>
        </a>
        <div className="header-actions">
          <BackendStatus health={health} onRecheck={onRecheck} />
          <button
            type="button"
            className="icon-button"
            onClick={() => onThemeChange(next)}
            aria-label={`Theme: ${label}. Switch to ${THEME_META[next].label.toLowerCase()}.`}
            title={`Theme: ${label}`}
          >
            <Icon />
          </button>
        </div>
      </div>
    </header>
  );
}
