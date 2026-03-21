/**
 * Web Audio API hook for capturing raw PCM audio from the microphone.
 *
 * Returns PCM i16 little-endian bytes suitable for whisper-rs transcription.
 * Uses ScriptProcessorNode for broad WebView compatibility.
 */

import { useCallback, useRef } from "react";

type AudioCaptureResult = {
  audioData: Uint8Array;
  sampleRate: number;
};

type StartCaptureOptions = {
  /** Callback fired on each audio process frame with RMS amplitude 0-1 */
  onLevel?: (level: number) => void;
};

export function useAudioCapture() {
  const streamRef = useRef<MediaStream | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const chunksRef = useRef<Float32Array[]>([]);

  const startCapture = useCallback(async (options?: StartCaptureOptions) => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
      },
    });

    const audioContext = new AudioContext({ sampleRate: 16000 });
    const source = audioContext.createMediaStreamSource(stream);

    // ScriptProcessorNode: deprecated but works everywhere including Tauri WebView
    const processor = audioContext.createScriptProcessor(4096, 1, 1);
    chunksRef.current = [];

    processor.onaudioprocess = (e) => {
      const input = e.inputBuffer.getChannelData(0);
      chunksRef.current.push(new Float32Array(input));

      if (options?.onLevel) {
        // Compute RMS amplitude
        let sum = 0;
        for (let i = 0; i < input.length; i++) {
          sum += input[i] * input[i];
        }
        const rms = Math.sqrt(sum / input.length);
        // Clamp to 0-1 range (RMS of a full-scale sine is ~0.707)
        const level = Math.min(1, rms / 0.5);
        options.onLevel(level);
      }
    };

    source.connect(processor);
    const silentGain = audioContext.createGain();
    silentGain.gain.value = 0;
    processor.connect(silentGain);
    silentGain.connect(audioContext.destination);

    streamRef.current = stream;
    contextRef.current = audioContext;
    processorRef.current = processor;
  }, []);

  const stopCapture = useCallback(async (): Promise<AudioCaptureResult> => {
    const sampleRate = contextRef.current?.sampleRate ?? 16000;

    // Stop all tracks
    streamRef.current?.getTracks().forEach((t) => t.stop());
    processorRef.current?.disconnect();

    if (contextRef.current?.state !== "closed") {
      await contextRef.current?.close();
    }

    // Merge chunks into single buffer
    const totalLength = chunksRef.current.reduce((sum, c) => sum + c.length, 0);
    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of chunksRef.current) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }
    chunksRef.current = [];

    // Convert f32 [-1.0, 1.0] to i16 little-endian bytes
    const i16Buffer = new ArrayBuffer(merged.length * 2);
    const view = new DataView(i16Buffer);
    for (let i = 0; i < merged.length; i++) {
      const clamped = Math.max(-1, Math.min(1, merged[i]));
      const val = clamped < 0 ? clamped * 32768 : clamped * 32767;
      view.setInt16(i * 2, val, true); // little-endian
    }

    streamRef.current = null;
    contextRef.current = null;
    processorRef.current = null;

    return {
      audioData: new Uint8Array(i16Buffer),
      sampleRate,
    };
  }, []);

  return { startCapture, stopCapture };
}
