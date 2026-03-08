import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import VoiceCommandArea from "./VoiceCommandArea";

vi.mock("next/link", () => ({
  default: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

const mockToggle = vi.fn();
const mockDismissResponse = vi.fn();
const mockConfirmAction = vi.fn();
const mockRejectAction = vi.fn();

vi.mock("@/hooks/useVoice", () => ({
  useVoice: vi.fn(() => ({
    state: "idle" as const,
    sttBackend: "web-speech" as const,
    lastResponse: null,
    audioLevel: 0,
    pendingAction: null,
    toggle: mockToggle,
    dismissResponse: mockDismissResponse,
    confirmAction: mockConfirmAction,
    rejectAction: mockRejectAction,
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
    pendingAction: null,
    toggle: mockToggle,
    dismissResponse: mockDismissResponse,
    confirmAction: mockConfirmAction,
    rejectAction: mockRejectAction,
  });
});

describe("VoiceCommandArea", () => {
  it("renders mic button in idle state", () => {
    render(<VoiceCommandArea pending={0} />);
    expect(screen.getByLabelText("Speak")).toBeInTheDocument();
    expect(screen.getByText(/Tap to speak/)).toBeInTheDocument();
  });

  it("calls toggle on mic button click", () => {
    render(<VoiceCommandArea pending={0} />);
    fireEvent.click(screen.getByLabelText("Speak"));
    expect(mockToggle).toHaveBeenCalled();
  });

  it("shows waveform bars during listening", () => {
    mockedUseVoice.mockReturnValue({
      state: "listening",
      sttBackend: "web-speech",
      lastResponse: null,
      audioLevel: 0.5,
      pendingAction: null,
      toggle: mockToggle,
      dismissResponse: mockDismissResponse,
      confirmAction: mockConfirmAction,
      rejectAction: mockRejectAction,
    });
    render(<VoiceCommandArea pending={0} />);
    expect(screen.getByText("Listening...")).toBeInTheDocument();
    expect(screen.getByLabelText("Listening...")).toBeInTheDocument();
  });

  it("shows bouncing dots during speaking", () => {
    mockedUseVoice.mockReturnValue({
      state: "speaking",
      sttBackend: "web-speech",
      lastResponse: "Test response",
      audioLevel: 0,
      pendingAction: null,
      toggle: mockToggle,
      dismissResponse: mockDismissResponse,
      confirmAction: mockConfirmAction,
      rejectAction: mockRejectAction,
    });
    render(<VoiceCommandArea pending={0} />);
    expect(screen.getByText("Speaking...")).toBeInTheDocument();
  });

  it("displays last response and dismisses on click", () => {
    mockedUseVoice.mockReturnValue({
      state: "idle",
      sttBackend: "web-speech",
      lastResponse: "You have 3 errors",
      audioLevel: 0,
      pendingAction: null,
      toggle: mockToggle,
      dismissResponse: mockDismissResponse,
      confirmAction: mockConfirmAction,
      rejectAction: mockRejectAction,
    });
    render(<VoiceCommandArea pending={5} />);
    fireEvent.click(screen.getByText("You have 3 errors"));
    expect(mockDismissResponse).toHaveBeenCalled();
  });

  it("shows pending count and Start Triage link", () => {
    render(<VoiceCommandArea pending={5} />);
    expect(screen.getByText("5 pending items")).toBeInTheDocument();
    expect(screen.getByText("Start Triage")).toBeInTheDocument();
    expect(screen.getByText("Start Triage").closest("a")).toHaveAttribute("href", "/triage");
  });

  it("shows View Dashboard when no pending items", () => {
    render(<VoiceCommandArea pending={0} />);
    expect(screen.getByText(/All clear/)).toBeInTheDocument();
    expect(screen.getByText("View Dashboard")).toBeInTheDocument();
    expect(screen.getByText("View Dashboard").closest("a")).toHaveAttribute("href", "/dashboard");
  });

  it("uses singular grammar for 1 pending item", () => {
    render(<VoiceCommandArea pending={1} />);
    expect(screen.getByText("1 pending item")).toBeInTheDocument();
  });
});
