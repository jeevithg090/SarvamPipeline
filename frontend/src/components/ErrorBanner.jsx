import { AlertIcon, XIcon } from './icons.jsx';

export default function ErrorBanner({ error, onDismiss }) {
  if (!error) return null;
  return (
    <div className="alert" role="alert">
      <AlertIcon className="alert-icon" />
      <div className="alert-body">
        <p className="alert-title">{error.title}</p>
        {error.hint && <p className="alert-hint">{error.hint}</p>}
      </div>
      <button
        type="button"
        className="icon-button icon-button-sm"
        onClick={onDismiss}
        aria-label="Dismiss error"
      >
        <XIcon width={18} height={18} />
      </button>
    </div>
  );
}
