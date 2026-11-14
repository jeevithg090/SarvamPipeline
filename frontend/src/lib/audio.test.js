import { describe, expect, it } from 'vitest';
import { floatTo16BitPCM, pcm16ToFloat32 } from './audio.js';

describe('floatTo16BitPCM', () => {
  it('maps the float range onto int16 and clamps', () => {
    const out = floatTo16BitPCM(new Float32Array([0, 1, -1, 0.5, 2, -2]));
    expect(Array.from(out)).toEqual([0, 32767, -32768, 16383, 32767, -32768]);
  });
});

describe('pcm16ToFloat32', () => {
  it('decodes int16 samples to floats', () => {
    const pcm = new Int16Array([0, 16384, -32768]).buffer;
    expect(Array.from(pcm16ToFloat32(pcm))).toEqual([0, 0.5, -1]);
  });

  it('ignores a trailing odd byte', () => {
    const buf = new ArrayBuffer(5);
    expect(pcm16ToFloat32(buf)).toHaveLength(2);
  });

  it('round-trips within quantisation error', () => {
    const input = new Float32Array([0.25, -0.75, 0.1]);
    const output = pcm16ToFloat32(floatTo16BitPCM(input).buffer);
    output.forEach((v, i) => expect(v).toBeCloseTo(input[i], 3));
  });
});
