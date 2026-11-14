/** PCM helpers for the browser <-> backend audio stream. */

export const MIC_SAMPLE_RATE = 16000;
export const AGENT_SAMPLE_RATE = 24000;

/** Convert Web Audio float samples (-1..1) to 16-bit signed PCM. */
export function floatTo16BitPCM(float32) {
  const int16 = new Int16Array(float32.length);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return int16;
}

/** Convert 16-bit signed PCM (as an ArrayBuffer) to Web Audio float samples. */
export function pcm16ToFloat32(arrayBuffer) {
  const int16 = new Int16Array(arrayBuffer, 0, Math.floor(arrayBuffer.byteLength / 2));
  const float32 = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 32768;
  return float32;
}
