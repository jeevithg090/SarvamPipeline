/**
 * User-facing error descriptions. Each has a short `title` and an
 * actionable `hint` so the person knows what to do next.
 */
export function micError(err) {
  if (err?.name === 'NotAllowedError' || err?.name === 'SecurityError') {
    return {
      title: 'Microphone access was denied.',
      hint: "Allow microphone access for this site in your browser's address bar or site settings, then start the call again.",
    };
  }
  if (err?.name === 'NotFoundError' || err?.name === 'OverconstrainedError') {
    return {
      title: 'No microphone was found.',
      hint: 'Connect a microphone or headset and try again.',
    };
  }
  if (err?.name === 'NotReadableError') {
    return {
      title: 'The microphone is busy.',
      hint: 'Another app may be using it. Close that app and try again.',
    };
  }
  return {
    title: 'Could not start audio.',
    hint: String(err?.message || err || 'Unknown error'),
  };
}

export const BACKEND_UNREACHABLE = {
  title: 'Could not reach the voice agent backend.',
  hint: 'Make sure the backend is running (python main.py in backend/) and that this page’s origin is listed in ALLOWED_ORIGINS.',
};

export const UNSUPPORTED_BROWSER = {
  title: 'This browser cannot record audio.',
  hint: 'Open the page in a recent Chrome, Edge or Safari over HTTPS or localhost.',
};

/** Error event sent by the backend over the websocket. */
export function backendError(description) {
  const text = description || 'Something went wrong.';
  if (/SARVAM_API_KEY/i.test(text)) {
    return {
      title: 'The backend has no Sarvam API key.',
      hint: 'Set SARVAM_API_KEY in backend/.env and restart the backend.',
    };
  }
  return { title: text, hint: '' };
}
