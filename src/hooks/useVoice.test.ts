import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useVoice } from "./useVoice";

vi.mock("@/lib/api", () => ({
  processVoice: vi.fn(),
}));

vi.mock("@/lib/whisper", () => ({
  isTauri: vi.fn(() => false),
  getModelStatus: vi.fn(),
  transcribe: vi.fn(),
}));

const mockStartCapture = vi.fn();
const mockStopCapture = vi.fn();
vi.mock("@/hooks/useAudioCapture", () => ({
  useAudioCapture: vi.fn(() => ({
    startCapture: mockStartCapture,
    stopCapture: mockStopCapture,
  })),
}));

class MockSpeechRecognition {
  lang = "";
  continuous = false;
  interimResults = false;
  onresult: ((e: unknown) => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  onend: (() => void) | null = null;
  start = vi.fn();
  stop = vi.fn();
}

const mockSpeak = vi.fn();
const mockCancel = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();

  Object.defineProperty(window, "SpeechRecognition", {
    value: MockSpeechRecognition,
    writable: true,
  });
  Object.defineProperty(window, "webkitSpeechRecognition", {
    value: undefined,
    writable: true,
  });
  Object.defineProperty(window, "speechSynthesis", {
    value: { speak: mockSpeak, cancel: mockCancel, getVoices: vi.fn(() => []) },
    writable: true,
    configurable: true,
  });
});

describe("useVoice", () => {
  it("starts in idle state with web-speech backend", async () => {
    const { result } = renderHook(() => useVoice());
    await act(async () => {});
    expect(result.current.state).toBe("idle");
    expect(result.current.sttBackend).toBe("web-speech");
    expect(result.current.lastResponse).toBeNull();
    expect(result.current.audioLevel).toBe(0);
  });

  it("toggles to listening state on toggle()", async () => {
    const { result } = renderHook(() => useVoice());
    await act(async () => {});

    act(() => {
      result.current.toggle();
    });

    expect(result.current.state).toBe("listening");
  });

  it("sets sttBackend to none when no SpeechRecognition", async () => {
    Object.defineProperty(window, "SpeechRecognition", { value: undefined, writable: true });
    Object.defineProperty(window, "webkitSpeechRecognition", { value: undefined, writable: true });

    const { result } = renderHook(() => useVoice());
    await act(async () => {});

    expect(result.current.sttBackend).toBe("none");
  });

  it("shows not supported message when toggling with no backend", async () => {
    Object.defineProperty(window, "SpeechRecognition", { value: undefined, writable: true });
    Object.defineProperty(window, "webkitSpeechRecognition", { value: undefined, writable: true });

    const { result } = renderHook(() => useVoice());
    await act(async () => {});

    act(() => {
      result.current.toggle();
    });

    expect(result.current.lastResponse).toBe("Speech recognition not supported.");
  });

  it("dismisses response and cancels speech", async () => {
    Object.defineProperty(window, "SpeechRecognition", { value: undefined, writable: true });

    const { result } = renderHook(() => useVoice());
    await act(async () => {});

    // Trigger a response by toggling with no backend
    act(() => {
      result.current.toggle();
    });

    // Now dismiss
    act(() => {
      result.current.dismissResponse();
    });

    expect(result.current.lastResponse).toBeNull();
    expect(result.current.state).toBe("idle");
    expect(mockCancel).toHaveBeenCalled();
  });

  it("responds to Cmd+Shift+Space keyboard shortcut", async () => {
    const { result } = renderHook(() => useVoice());
    await act(async () => {});

    act(() => {
      window.dispatchEvent(
        new KeyboardEvent("keydown", {
          code: "Space",
          metaKey: true,
          shiftKey: true,
          bubbles: true,
        }),
      );
    });

    expect(result.current.state).toBe("listening");
  });
});
