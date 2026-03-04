import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import DashboardPage from "./page";
import type { TriageItem } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getTriageItems: vi.fn(),
}));

import { getTriageItems } from "@/lib/api";
const mockedGetTriageItems = vi.mocked(getTriageItems);

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
    status: "snoozed",
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

describe("DashboardPage", () => {
  // Shows loading state while fetching
  it("shows loading state initially", () => {
    mockedGetTriageItems.mockReturnValue(new Promise(() => {}));
    render(<DashboardPage />);
    expect(screen.getByText("Loading events...")).toBeInTheDocument();
  });

  // Shows empty state when no events exist
  it("shows empty state when no items", async () => {
    mockedGetTriageItems.mockResolvedValue([]);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText(/No events yet/)).toBeInTheDocument();
    });
  });

  // Renders event cards with title and severity
  it("renders event cards with titles", async () => {
    mockedGetTriageItems.mockResolvedValue(sampleItems);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("TypeError in dashboard")).toBeInTheDocument();
    });
    expect(screen.getByText("CVE-2024-1234")).toBeInTheDocument();
  });

  // Severity badges are rendered
  it("shows severity badges", async () => {
    mockedGetTriageItems.mockResolvedValue(sampleItems);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("critical")).toBeInTheDocument();
    });
    expect(screen.getByText("high")).toBeInTheDocument();
  });

  // Status badges are rendered
  it("shows status badges", async () => {
    mockedGetTriageItems.mockResolvedValue(sampleItems);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("pending")).toBeInTheDocument();
    });
    expect(screen.getByText("snoozed")).toBeInTheDocument();
  });

  // Occurrence count displayed
  it("shows occurrence counts", async () => {
    mockedGetTriageItems.mockResolvedValue(sampleItems);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText("3x")).toBeInTheDocument();
    });
    expect(screen.getByText("1x")).toBeInTheDocument();
  });

  // Fetches all items (no status filter)
  it("fetches items without status filter", async () => {
    mockedGetTriageItems.mockResolvedValue([]);
    render(<DashboardPage />);
    await waitFor(() => {
      expect(mockedGetTriageItems).toHaveBeenCalledWith();
    });
  });
});
