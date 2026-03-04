import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import StatusBar from "./StatusBar";

const mockStatus = {
  critical_count: 2,
  vulnerability_count: 5,
  actioned_today: 3,
  pending_count: 8,
};

vi.mock("@/lib/api", () => ({
  getStatus: vi.fn(),
}));

import { getStatus } from "@/lib/api";
const mockedGetStatus = vi.mocked(getStatus);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("StatusBar", () => {
  it("shows loading skeleton when data is not yet loaded", () => {
    mockedGetStatus.mockReturnValue(new Promise(() => {})); // never resolves
    render(<StatusBar />);
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBe(4);
  });

  it("renders metric cards after data loads", async () => {
    mockedGetStatus.mockResolvedValue(mockStatus);
    render(<StatusBar />);
    await waitFor(() => {
      expect(screen.getByText("2")).toBeInTheDocument();
    });
    expect(screen.getByText("Critical")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("Vulns")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Actioned")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });
});
