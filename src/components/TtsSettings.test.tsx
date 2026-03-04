import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TtsSettings from "./TtsSettings";

vi.mock("@/lib/whisper", () => ({
  isTauri: vi.fn(() => false),
  getModelStatus: vi.fn(),
}));

const mockSpeak = vi.fn();
const mockCancel = vi.fn();
const mockGetVoices = vi.fn(() => [
  { voiceURI: "voice-1", name: "Alice", lang: "en-US" },
  { voiceURI: "voice-2", name: "Bob", lang: "en-GB" },
]);

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();

  Object.defineProperty(window, "SpeechRecognition", {
    value: class {},
    writable: true,
  });

  vi.stubGlobal("SpeechSynthesisUtterance", class {
    text = "";
    rate = 1;
    voice: unknown = null;
    constructor(text?: string) { this.text = text ?? ""; }
  });

  Object.defineProperty(window, "speechSynthesis", {
    value: {
      speak: mockSpeak,
      cancel: mockCancel,
      getVoices: mockGetVoices,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    },
    writable: true,
    configurable: true,
  });
});

describe("TtsSettings", () => {
  it("shows STT backend indicator", async () => {
    render(<TtsSettings />);
    expect(await screen.findByText("Web Speech API (browser)")).toBeInTheDocument();
  });

  it("shows keyboard shortcut hint", () => {
    render(<TtsSettings />);
    expect(screen.getByText(/⌘⇧Space/)).toBeInTheDocument();
  });

  it("renders voice dropdown with system default", () => {
    render(<TtsSettings />);
    expect(screen.getByText("System default")).toBeInTheDocument();
  });

  it("renders speech rate slider", () => {
    render(<TtsSettings />);
    expect(screen.getByText(/Speech Rate/)).toBeInTheDocument();
    expect(screen.getByRole("slider")).toBeInTheDocument();
  });

  it("saves voice selection to localStorage", () => {
    render(<TtsSettings />);
    const select = screen.getByRole("combobox");
    fireEvent.change(select, { target: { value: "voice-1" } });
    expect(localStorage.getItem("clarity-tts-voice-uri")).toBe("voice-1");
  });

  it("saves rate to localStorage", () => {
    render(<TtsSettings />);
    const slider = screen.getByRole("slider");
    fireEvent.change(slider, { target: { value: "1.5" } });
    expect(localStorage.getItem("clarity-tts-rate")).toBe("1.5");
  });

  it("speaks preview on button click", () => {
    render(<TtsSettings />);
    fireEvent.click(screen.getByText("Preview Voice"));
    expect(mockCancel).toHaveBeenCalled();
    expect(mockSpeak).toHaveBeenCalled();
  });

  it("shows not supported when no SpeechRecognition", async () => {
    Object.defineProperty(window, "SpeechRecognition", { value: undefined, writable: true });
    Object.defineProperty(window, "webkitSpeechRecognition", { value: undefined, writable: true });
    render(<TtsSettings />);
    expect(await screen.findByText("Not supported")).toBeInTheDocument();
  });
});
