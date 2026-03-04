import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import MorningBriefCard from "./MorningBrief";

vi.mock("@/lib/api", () => ({
  getMorningBrief: vi.fn(),
}));

import { getMorningBrief } from "@/lib/api";
const mockedGetMorningBrief = vi.mocked(getMorningBrief);

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

const sampleBrief = {
  new_errors_24h: 3,
  new_vulns_24h: 1,
  actioned_yesterday: 5,
  pending_total: 8,
  top_severity: "critical",
};

describe("MorningBriefCard", () => {
  // Shows brief when never seen today
  it("renders brief data when not yet dismissed today", async () => {
    mockedGetMorningBrief.mockResolvedValue(sampleBrief);
    render(<MorningBriefCard />);
    await waitFor(() => {
      expect(screen.getByText("Morning Brief")).toBeInTheDocument();
    });
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("new errors")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("new vulns")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("critical")).toBeInTheDocument();
  });

  // Does not show if already dismissed today
  it("does not render if already dismissed today", async () => {
    localStorage.setItem("clarity-last-brief-date", new Date().toDateString());
    mockedGetMorningBrief.mockResolvedValue(sampleBrief);
    render(<MorningBriefCard />);
    // Wait a tick and verify nothing appeared
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.queryByText("Morning Brief")).not.toBeInTheDocument();
    expect(mockedGetMorningBrief).not.toHaveBeenCalled();
  });

  // Dismiss hides the brief and stores today's date
  it("hides brief and saves date on dismiss", async () => {
    mockedGetMorningBrief.mockResolvedValue(sampleBrief);
    render(<MorningBriefCard />);
    await waitFor(() => {
      expect(screen.getByText("Morning Brief")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Dismiss"));
    expect(screen.queryByText("Morning Brief")).not.toBeInTheDocument();
    expect(localStorage.getItem("clarity-last-brief-date")).toBe(new Date().toDateString());
  });
});
