import { describe, expect, it } from 'vitest';
import { backendError, micError } from './errors.js';

describe('micError', () => {
  it('explains denied permission', () => {
    expect(micError({ name: 'NotAllowedError' }).title).toMatch(/denied/);
  });

  it('explains a missing microphone', () => {
    expect(micError({ name: 'NotFoundError' }).title).toMatch(/No microphone/);
  });

  it('falls back to the error message', () => {
    expect(micError(new Error('boom')).hint).toBe('boom');
  });
});

describe('backendError', () => {
  it('turns a missing key into setup advice', () => {
    expect(backendError('SARVAM_API_KEY not set').hint).toMatch(/backend\/\.env/);
  });

  it('passes other messages through', () => {
    expect(backendError('TTS error')).toEqual({ title: 'TTS error', hint: '' });
  });
});
