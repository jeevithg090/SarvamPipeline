export const LLM_MODELS = ['sarvam-30b', 'sarvam-105b'];

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

export function defaultWsUrl(llmModel) {
  return buildWsUrl(llmModel, {
    envUrl: import.meta.env.VITE_WS_URL,
    location: window.location,
  });
}
