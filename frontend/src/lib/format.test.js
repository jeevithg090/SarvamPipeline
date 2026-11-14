import { describe, expect, it } from 'vitest';
import { formatDuration, transcriptToText } from './format.js';

describe('formatDuration', () => {
  it('formats minutes and seconds', () => {
    expect(formatDuration(0)).toBe('0:00');
    expect(formatDuration(65)).toBe('1:05');
    expect(formatDuration(59.9)).toBe('0:59');
  });

  it('adds hours past an hour and clamps negatives', () => {
    expect(formatDuration(3725)).toBe('1:02:05');
    expect(formatDuration(-3)).toBe('0:00');
  });
});

describe('transcriptToText', () => {
  it('labels each speaker', () => {
    const text = transcriptToText([
      { role: 'user', content: 'Namaste' },
      { role: 'assistant', content: 'Namaste! Kaise madad karun?' },
    ]);
    expect(text).toBe('You: Namaste\nAgent: Namaste! Kaise madad karun?');
  });
});
