import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import VoiceButton from "./VoiceButton";

const mockToggle = vi.fn();
const mockDismissResponse = vi.fn();

vi.mock("@/hooks/useVoice", () => ({
  useVoice: vi.fn(() => ({
    state: "idle" as const,
    sttBackend: "web-speech" as const,
    lastResponse: null,
    audioLevel: 0,
    toggle: mockToggle,
    dismissResponse: mockDismissResponse,
  })),
}));

import { useVoice } from "@/hooks/useVoice";
const mockedUseVoice = vi.mocked(useVoice);

beforeEach(() => {
  vi.clearAllMocks();
  mockedUseVoice.mockReturnValue({
    state: "idle",
    sttBackend: "web-speech",
    lastResponse: null,
    audioLevel: 0,
    toggle: mockToggle,
    dismissResponse: mockDismissResponse,
  });
});

describe("VoiceButton", () => {
  it("renders mic button in idle state", () => {
    render(<VoiceButton />);
    expect(screen.getByLabelText("Speak")).toBeInTheDocument();
  });

  it("calls toggle on click", () => {
    render(<VoiceButton />);
    fireEvent.click(screen.getByLabelText("Speak"));
    expect(mockToggle).toHaveBeenCalled();
  });

  it("shows listening state", () => {
    mockedUseVoice.mockReturnValue({
      state: "listening",
      sttBackend: "web-speech",
      lastResponse: null,
      audioLevel: 0.5,
      toggle: mockToggle,
      dismissResponse: mockDismissResponse,
    });
    render(<VoiceButton />);
    expect(screen.getByLabelText("Listening...")).toBeInTheDocument();
  });

  it("shows processing state with disabled button", () => {
    mockedUseVoice.mockReturnValue({
      state: "processing",
      sttBackend: "web-speech",
      lastResponse: null,
      audioLevel: 0,
      toggle: mockToggle,
      dismissResponse: mockDismissResponse,
    });
    render(<VoiceButton />);
    expect(screen.getByLabelText("Thinking...")).toBeDisabled();
  });

  it("shows speaking state", () => {
    mockedUseVoice.mockReturnValue({
      state: "speaking",
      sttBackend: "web-speech",
      lastResponse: "Hello",
      audioLevel: 0,
      toggle: mockToggle,
      dismissResponse: mockDismissResponse,
    });
    render(<VoiceButton />);
    expect(screen.getByLabelText("Speaking...")).toBeInTheDocument();
  });

  it("displays and dismisses response", () => {
    mockedUseVoice.mockReturnValue({
      state: "idle",
      sttBackend: "web-speech",
      lastResponse: "2 items pending",
      audioLevel: 0,
      toggle: mockToggle,
      dismissResponse: mockDismissResponse,
    });
    render(<VoiceButton />);
    expect(screen.getByText("2 items pending")).toBeInTheDocument();
    fireEvent.click(screen.getByText("2 items pending"));
    expect(mockDismissResponse).toHaveBeenCalled();
  });
});
