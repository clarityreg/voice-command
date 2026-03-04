import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import StatsPage from "./page";

vi.mock("@/lib/api");

import { getStats } from "@/lib/api";

const mockStats = {
  weekly_resolved: 12,
  avg_triage_hours: 3.5,
  trend: [
    { date: "2026-02-25", count: 2 },
    { date: "2026-02-26", count: 0 },
    { date: "2026-02-27", count: 5 },
  ],
  severity_breakdown: { critical: 3, high: 5, medium: 8, low: 2 },
};

describe("StatsPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows loading state", () => {
    vi.mocked(getStats).mockReturnValue(new Promise(() => {}));
    render(<StatsPage />);
    expect(screen.getByText("Loading statistics...")).toBeInTheDocument();
  });

  it("renders stats after loading", async () => {
    vi.mocked(getStats).mockResolvedValue(mockStats);
    render(<StatsPage />);
    await waitFor(() => {
      expect(screen.getByText("12")).toBeInTheDocument();
    });
    expect(screen.getByText("3.5h")).toBeInTheDocument();
    expect(screen.getByText("Statistics")).toBeInTheDocument();
  });

  it("shows severity breakdown", async () => {
    vi.mocked(getStats).mockResolvedValue(mockStats);
    render(<StatsPage />);
    await waitFor(() => {
      expect(screen.getByText("3")).toBeInTheDocument(); // critical
    });
    expect(screen.getByText("5")).toBeInTheDocument(); // high
    expect(screen.getByText("8")).toBeInTheDocument(); // medium
  });

  it("shows dash when avg_triage_hours is null", async () => {
    vi.mocked(getStats).mockResolvedValue({
      ...mockStats,
      avg_triage_hours: null,
    });
    render(<StatsPage />);
    await waitFor(() => {
      expect(screen.getByText("—")).toBeInTheDocument();
    });
  });

  it("shows error on fetch failure", async () => {
    vi.mocked(getStats).mockRejectedValue(new Error("fail"));
    render(<StatsPage />);
    await waitFor(() => {
      expect(screen.getByText(/Could not load statistics/)).toBeInTheDocument();
    });
  });

  it("renders trend chart bars", async () => {
    vi.mocked(getStats).mockResolvedValue(mockStats);
    render(<StatsPage />);
    await waitFor(() => {
      expect(screen.getByText("Daily Resolved (14d)")).toBeInTheDocument();
    });
  });
});
