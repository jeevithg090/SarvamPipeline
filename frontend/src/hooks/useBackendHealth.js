import { useCallback, useEffect, useState } from 'react';
import { defaultHealthUrl } from '../lib/config.js';

const TIMEOUT_MS = 4000;

async function fetchHealth(signal) {
  const res = await fetch(defaultHealthUrl(), { signal, cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const body = await res.json();
  return body.sarvam_key ? 'ready' : 'no-key';
}

/**
 * Polls the backend's `/health` endpoint once on load (and on demand) so the
 * UI can warn before a call is started.
 *
 * `state` is checking | ready | no-key | offline.
 */
export function useBackendHealth() {
  const [state, setState] = useState('checking');
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
    fetchHealth(controller.signal)
      .then((next) => !cancelled && setState(next))
      .catch(() => !cancelled && setState('offline'))
      .finally(() => clearTimeout(timer));
    return () => {
      cancelled = true;
      clearTimeout(timer);
      controller.abort();
    };
  }, [nonce]);

  const recheck = useCallback(() => {
    setState('checking');
    setNonce((n) => n + 1);
  }, []);

  return { state, recheck };
}
