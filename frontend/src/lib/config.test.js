import { describe, expect, it } from 'vitest';
import { buildHealthUrl, buildWsUrl } from './config.js';

describe('buildWsUrl', () => {
  it('defaults to port 8004 on the page host', () => {
    const url = buildWsUrl('sarvam-30b', {
      location: { protocol: 'http:', hostname: '192.168.1.5' },
    });
    expect(url).toBe('ws://192.168.1.5:8004/ws?llm_model=sarvam-30b');
  });

  it('uses wss on https pages', () => {
    const url = buildWsUrl('sarvam-30b', {
      location: { protocol: 'https:', hostname: 'example.com' },
    });
    expect(url.startsWith('wss://example.com:8004/ws')).toBe(true);
  });

  it('honours an explicit URL and encodes the model', () => {
    const url = buildWsUrl('a b', { envUrl: 'wss://api.example.com/ws?x=1' });
    expect(url).toBe('wss://api.example.com/ws?x=1&llm_model=a+b');
  });
});

describe('buildHealthUrl', () => {
  it('maps ws to http and /ws to /health', () => {
    expect(buildHealthUrl('ws://localhost:8004/ws?llm_model=sarvam-30b')).toBe(
      'http://localhost:8004/health',
    );
  });

  it('maps wss to https and keeps a path prefix', () => {
    expect(buildHealthUrl('wss://example.com/voice/ws')).toBe('https://example.com/voice/health');
  });
});
