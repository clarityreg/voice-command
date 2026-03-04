import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAudioCapture } from "./useAudioCapture";

const mockStop = vi.fn();
const mockGetChannelData = vi.fn(() => new Float32Array([0.1, -0.2, 0.3]));

let processorCallback: ((e: unknown) => void) | null = null;

const mockProcessor = {
  set onaudioprocess(cb: ((e: unknown) => void) | null) {
    processorCallback = cb;
  },
  get onaudioprocess() {
    return processorCallback;
  },
  connect: vi.fn(),
  disconnect: vi.fn(),
};

const mockSource = {
  connect: vi.fn(),
};

const mockAudioContext = {
  sampleRate: 16000,
  state: "running",
  createMediaStreamSource: vi.fn(() => mockSource),
  createScriptProcessor: vi.fn(() => mockProcessor),
  close: vi.fn().mockResolvedValue(undefined),
  destination: {},
};

beforeEach(() => {
  vi.clearAllMocks();
  processorCallback = null;

  Object.defineProperty(navigator, "mediaDevices", {
    value: {
      getUserMedia: vi.fn().mockResolvedValue({
        getTracks: () => [{ stop: mockStop }],
      }),
    },
    writable: true,
    configurable: true,
  });

  vi.stubGlobal(
    "AudioContext",
    function AudioContext() {
      return mockAudioContext;
    },
  );
});

describe("useAudioCapture", () => {
  it("starts capture and requests microphone permission", async () => {
    const { result } = renderHook(() => useAudioCapture());

    await act(async () => {
      await result.current.startCapture();
    });

    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({
      audio: { channelCount: 1, sampleRate: 16000 },
    });
  });

  it("calls onLevel callback with RMS amplitude", async () => {
    const onLevel = vi.fn();
    const { result } = renderHook(() => useAudioCapture());

    await act(async () => {
      await result.current.startCapture({ onLevel });
    });

    // Simulate audio data via the processor callback
    if (processorCallback) {
      processorCallback({
        inputBuffer: { getChannelData: mockGetChannelData },
      });
    }

    expect(onLevel).toHaveBeenCalled();
    const level = onLevel.mock.calls[0][0];
    expect(level).toBeGreaterThan(0);
    expect(level).toBeLessThanOrEqual(1);
  });

  it("stops capture and returns PCM i16 LE bytes", async () => {
    const { result } = renderHook(() => useAudioCapture());

    await act(async () => {
      await result.current.startCapture();
    });

    // Simulate audio data via the processor callback
    if (processorCallback) {
      processorCallback({
        inputBuffer: { getChannelData: mockGetChannelData },
      });
    }

    let captureResult: { audioData: Uint8Array; sampleRate: number } | undefined;
    await act(async () => {
      captureResult = await result.current.stopCapture();
    });

    expect(captureResult).toBeDefined();
    expect(captureResult!.sampleRate).toBe(16000);
    expect(captureResult!.audioData).toBeInstanceOf(Uint8Array);
    // 3 samples * 2 bytes each = 6 bytes
    expect(captureResult!.audioData.length).toBe(6);
    expect(mockStop).toHaveBeenCalled();
  });
});
