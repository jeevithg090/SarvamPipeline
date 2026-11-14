export const LLM_MODELS = ['sarvam-30b', 'sarvam-105b'];

/** Short labels shown next to each model in the picker. */
export const MODEL_INFO = {
  'sarvam-30b': { label: 'Sarvam 30B', hint: 'Smaller model, quicker replies' },
  'sarvam-105b': { label: 'Sarvam 105B', hint: 'Larger model, more capable' },
};

/**
 * Websocket endpoint of the backend. `VITE_WS_URL` overrides it; otherwise
 * the backend is assumed on port 8004 of the host serving the page.
 */
export function buildWsUrl(llmModel, { envUrl, location } = {}) {
  let base = envUrl;
  if (!base) {
    const protocol = location?.protocol === 'https:' ? 'wss:' : 'ws:';
    const hostname = location?.hostname || 'localhost';
    base = `${protocol}//${hostname}:8004/ws`;
  }
  const url = new URL(base);
  url.searchParams.set('llm_model', llmModel);
  return url.toString();
}

/**
 * HTTP `/health` endpoint that sits next to a websocket URL, e.g.
 * `wss://api.example.com/ws` -> `https://api.example.com/health`.
 */
export function buildHealthUrl(wsUrl) {
  const url = new URL(wsUrl);
  url.protocol = url.protocol === 'wss:' ? 'https:' : 'http:';
  url.pathname = url.pathname.replace(/\/ws\/?$/, '') + '/health';
  url.search = '';
  url.hash = '';
  return url.toString();
}

export function defaultWsUrl(llmModel) {
  return buildWsUrl(llmModel, {
    envUrl: import.meta.env.VITE_WS_URL,
    location: window.location,
  });
}

export function defaultHealthUrl() {
  return buildHealthUrl(defaultWsUrl(LLM_MODELS[0]));
}
