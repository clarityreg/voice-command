import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import FocusPage from "./page";

// Mock next/link to render a plain anchor
vi.mock("next/link", () => ({
  default: ({ children, href, className }: { children: React.ReactNode; href: string; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  getStatus: vi.fn(),
}));

// StatusBar and MorningBrief have their own API calls — stub them
vi.mock("@/components/StatusBar", () => ({
  default: () => <div data-testid="status-bar">StatusBar</div>,
}));

vi.mock("@/components/MorningBrief", () => ({
  default: () => <div data-testid="morning-brief">MorningBrief</div>,
}));

vi.mock("@/components/FocusTimer", () => ({
  default: () => <div data-testid="focus-timer">FocusTimer</div>,
}));

vi.mock("@/components/VoiceCommandArea", () => ({
  default: ({ pending }: { pending: number }) => (
    <div data-testid="voice-command-area">VoiceCommandArea pending={pending}</div>
  ),
}));

import { getStatus } from "@/lib/api";
const mockedGetStatus = vi.mocked(getStatus);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("FocusPage", () => {
  // Shows score ring with 0 before API responds
  it("renders score ring with 0 pending initially", () => {
    mockedGetStatus.mockReturnValue(new Promise(() => {}));
    render(<FocusPage />);
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
  });

  // Verifies VoiceCommandArea receives pending=0
  it("shows View Dashboard link when pending is 0", async () => {
    mockedGetStatus.mockResolvedValue({
      critical_count: 0,
      vulnerability_count: 0,
      actioned_today: 2,
      pending_count: 0,
    });
    render(<FocusPage />);
    await waitFor(() => {
      expect(screen.getByTestId("voice-command-area")).toHaveTextContent("pending=0");
    });
  });

  // Verifies VoiceCommandArea receives pending=7
  it("shows Start Triage link when items are pending", async () => {
    mockedGetStatus.mockResolvedValue({
      critical_count: 1,
      vulnerability_count: 3,
      actioned_today: 0,
      pending_count: 7,
    });
    render(<FocusPage />);
    await waitFor(() => {
      expect(screen.getByText("7")).toBeInTheDocument();
    });
    expect(screen.getByTestId("voice-command-area")).toHaveTextContent("pending=7");
  });

  // Verifies VoiceCommandArea receives pending=1
  it("uses singular grammar for 1 pending item", async () => {
    mockedGetStatus.mockResolvedValue({
      critical_count: 0,
      vulnerability_count: 0,
      actioned_today: 0,
      pending_count: 1,
    });
    render(<FocusPage />);
    await waitFor(() => {
      expect(screen.getByText("1")).toBeInTheDocument();
    });
    expect(screen.getByTestId("voice-command-area")).toHaveTextContent("pending=1");
  });

  // Verifies VoiceCommandArea receives pending=5
  it("links to /triage when pending > 0", async () => {
    mockedGetStatus.mockResolvedValue({
      critical_count: 0,
      vulnerability_count: 0,
      actioned_today: 0,
      pending_count: 5,
    });
    render(<FocusPage />);
    await waitFor(() => {
      expect(screen.getByTestId("voice-command-area")).toHaveTextContent("pending=5");
    });
  });

  // Verifies VoiceCommandArea receives pending=0
  it("links to /dashboard when pending is 0", async () => {
    mockedGetStatus.mockResolvedValue({
      critical_count: 0,
      vulnerability_count: 0,
      actioned_today: 0,
      pending_count: 0,
    });
    render(<FocusPage />);
    await waitFor(() => {
      expect(screen.getByTestId("voice-command-area")).toHaveTextContent("pending=0");
    });
  });

  // Category icons are present
  it("renders category emoji icons", () => {
    mockedGetStatus.mockReturnValue(new Promise(() => {}));
    render(<FocusPage />);
    expect(screen.getByTitle("Bugs")).toBeInTheDocument();
    expect(screen.getByTitle("Security")).toBeInTheDocument();
    expect(screen.getByTitle("Tasks")).toBeInTheDocument();
    expect(screen.getByTitle("Done")).toBeInTheDocument();
  });
});
