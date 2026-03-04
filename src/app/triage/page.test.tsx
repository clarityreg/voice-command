import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import TriagePage from "./page";
import type { TriageItem } from "@/lib/api";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: () => "/triage",
}));

vi.mock("@/lib/api", () => ({
  getTriageItems: vi.fn(),
  snoozeItem: vi.fn(),
  dismissItem: vi.fn(),
  createIssue: vi.fn(),
  startAgentFix: vi.fn(),
}));

import { getTriageItems, snoozeItem, dismissItem, createIssue } from "@/lib/api";
const mockedGetTriageItems = vi.mocked(getTriageItems);
const mockedSnoozeItem = vi.mocked(snoozeItem);
const mockedDismissItem = vi.mocked(dismissItem);
const mockedCreateIssue = vi.mocked(createIssue);

const sampleItems: TriageItem[] = [
  {
    id: 1,
    source: "posthog",
    title: "TypeError in dashboard",
    description: "Cannot read property",
    severity: "critical",
    status: "pending",
    fingerprint: "abc",
    occurrence_count: 3,
    first_seen: "2026-03-01T10:00:00Z",
    last_seen: "2026-03-03T10:00:00Z",
    metadata: {},
  },
  {
    id: 2,
    source: "aikido",
    title: "CVE-2024-1234",
    description: "Prototype pollution",
    severity: "high",
    status: "pending",
    fingerprint: "def",
    occurrence_count: 1,
    first_seen: "2026-03-02T10:00:00Z",
    last_seen: "2026-03-03T10:00:00Z",
    metadata: {},
  },
];

beforeEach(() => {
  vi.clearAllMocks();
});

describe("TriagePage", () => {
  // Shows loading state while fetching
  it("shows loading state initially", () => {
    mockedGetTriageItems.mockReturnValue(new Promise(() => {}));
    render(<TriagePage />);
    expect(screen.getByText("Loading triage queue...")).toBeInTheDocument();
  });

  // Shows error state when backend unreachable
  it("shows error message when API fails", async () => {
    mockedGetTriageItems.mockRejectedValue(new Error("Network error"));
    render(<TriagePage />);
    await waitFor(() => {
      expect(screen.getByText(/Could not connect to backend/)).toBeInTheDocument();
    });
  });

  // Retry button re-fetches items
  it("retries fetch when Retry is clicked", async () => {
    mockedGetTriageItems.mockRejectedValueOnce(new Error("fail"));
    render(<TriagePage />);
    await waitFor(() => {
      expect(screen.getByText("Retry")).toBeInTheDocument();
    });
    mockedGetTriageItems.mockResolvedValueOnce([]);
    fireEvent.click(screen.getByText("Retry"));
    expect(mockedGetTriageItems).toHaveBeenCalledTimes(2);
  });

  // Shows "all clear" when queue is empty
  it("shows all clear when no items are pending", async () => {
    mockedGetTriageItems.mockResolvedValue([]);
    render(<TriagePage />);
    await waitFor(() => {
      expect(screen.getByText("All clear!")).toBeInTheDocument();
    });
  });

  // Renders first item from the queue
  it("renders the first triage item", async () => {
    mockedGetTriageItems.mockResolvedValue(sampleItems);
    render(<TriagePage />);
    await waitFor(() => {
      expect(screen.getByText("TypeError in dashboard")).toBeInTheDocument();
    });
    expect(screen.getByText("1 of 2")).toBeInTheDocument();
  });

  // Snooze advances to next item
  it("advances to next item after snooze", async () => {
    mockedGetTriageItems.mockResolvedValue(sampleItems);
    mockedSnoozeItem.mockResolvedValue(sampleItems[0]);
    render(<TriagePage />);
    await waitFor(() => {
      expect(screen.getByText("TypeError in dashboard")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Snooze"));
    await waitFor(() => {
      expect(screen.getByText("CVE-2024-1234")).toBeInTheDocument();
    });
  });

  // Dismiss advances to next item
  it("advances to next item after dismiss", async () => {
    mockedGetTriageItems.mockResolvedValue(sampleItems);
    mockedDismissItem.mockResolvedValue(sampleItems[0]);
    render(<TriagePage />);
    await waitFor(() => {
      expect(screen.getByText("TypeError in dashboard")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Dismiss"));
    await waitFor(() => {
      expect(screen.getByText("CVE-2024-1234")).toBeInTheDocument();
    });
  });

  // Create issue advances to next item
  it("advances to next item after creating issue", async () => {
    mockedGetTriageItems.mockResolvedValue(sampleItems);
    mockedCreateIssue.mockResolvedValue({});
    render(<TriagePage />);
    await waitFor(() => {
      expect(screen.getByText("TypeError in dashboard")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Create Issue"));
    await waitFor(() => {
      expect(screen.getByText("CVE-2024-1234")).toBeInTheDocument();
    });
  });

  // Re-fetches when last item is actioned
  it("re-fetches when actioning the last item", async () => {
    mockedGetTriageItems.mockResolvedValueOnce([sampleItems[0]]);
    mockedSnoozeItem.mockResolvedValue(sampleItems[0]);
    render(<TriagePage />);
    await waitFor(() => {
      expect(screen.getByText("TypeError in dashboard")).toBeInTheDocument();
    });
    mockedGetTriageItems.mockResolvedValueOnce([]);
    fireEvent.click(screen.getByText("Snooze"));
    await waitFor(() => {
      expect(mockedGetTriageItems).toHaveBeenCalledTimes(2);
    });
  });

  // Keyboard shortcut 'c' triggers Create Issue
  it("keyboard 'c' creates issue on current item", async () => {
    mockedGetTriageItems.mockResolvedValue(sampleItems);
    mockedCreateIssue.mockResolvedValue({});
    render(<TriagePage />);
    await waitFor(() => {
      expect(screen.getByText("TypeError in dashboard")).toBeInTheDocument();
    });
    fireEvent.keyDown(window, { key: "c" });
    await waitFor(() => {
      expect(mockedCreateIssue).toHaveBeenCalledWith(1);
    });
  });

  // Keyboard shortcut 's' triggers Snooze
  it("keyboard 's' snoozes current item", async () => {
    mockedGetTriageItems.mockResolvedValue(sampleItems);
    mockedSnoozeItem.mockResolvedValue(sampleItems[0]);
    render(<TriagePage />);
    await waitFor(() => {
      expect(screen.getByText("TypeError in dashboard")).toBeInTheDocument();
    });
    fireEvent.keyDown(window, { key: "s" });
    await waitFor(() => {
      expect(mockedSnoozeItem).toHaveBeenCalledWith(1);
    });
  });

  // Keyboard shortcut 'd' triggers Dismiss
  it("keyboard 'd' dismisses current item", async () => {
    mockedGetTriageItems.mockResolvedValue(sampleItems);
    mockedDismissItem.mockResolvedValue(sampleItems[0]);
    render(<TriagePage />);
    await waitFor(() => {
      expect(screen.getByText("TypeError in dashboard")).toBeInTheDocument();
    });
    fireEvent.keyDown(window, { key: "d" });
    await waitFor(() => {
      expect(mockedDismissItem).toHaveBeenCalledWith(1);
    });
  });

  // Keyboard shortcut '?' toggles help overlay
  it("keyboard '?' toggles shortcut help", async () => {
    mockedGetTriageItems.mockResolvedValue(sampleItems);
    render(<TriagePage />);
    await waitFor(() => {
      expect(screen.getByText("TypeError in dashboard")).toBeInTheDocument();
    });
    fireEvent.keyDown(window, { key: "?" });
    expect(screen.getByText("Keyboard Shortcuts")).toBeInTheDocument();
  });

  // Shows ? button for opening help
  it("shows ? button for keyboard shortcuts", async () => {
    mockedGetTriageItems.mockResolvedValue(sampleItems);
    render(<TriagePage />);
    await waitFor(() => {
      expect(screen.getByTitle("Keyboard shortcuts")).toBeInTheDocument();
    });
  });
});
