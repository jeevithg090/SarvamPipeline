// AudioWorklet that batches microphone samples into fixed-size frames and
// posts them to the main thread, which converts them to PCM and sends them
// to the backend. Runs on the audio rendering thread.
const FRAME_SIZE = 4096;

class MicCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Float32Array(FRAME_SIZE);
    this.offset = 0;
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (channel) {
      let read = 0;
      while (read < channel.length) {
        const n = Math.min(channel.length - read, FRAME_SIZE - this.offset);
        this.buffer.set(channel.subarray(read, read + n), this.offset);
        this.offset += n;
        read += n;
        if (this.offset === FRAME_SIZE) {
          const frame = this.buffer;
          this.port.postMessage(frame, [frame.buffer]);
          this.buffer = new Float32Array(FRAME_SIZE);
          this.offset = 0;
        }
      }
    }
    return true;
  }
}

registerProcessor('mic-capture', MicCaptureProcessor);
