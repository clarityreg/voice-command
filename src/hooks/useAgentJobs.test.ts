import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useAgentJobs } from "./useAgentJobs";

vi.mock("@/lib/api", () => ({
  getAgentJobs: vi.fn(),
  approveAgentPlan: vi.fn(),
  cancelAgentJob: vi.fn(),
}));

vi.mock("@/lib/wsClient", () => ({
  createWsClient: vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
  })),
}));

import { getAgentJobs } from "@/lib/api";
const mockedGetAgentJobs = vi.mocked(getAgentJobs);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useAgentJobs", () => {
  it("returns empty jobs initially", () => {
    mockedGetAgentJobs.mockResolvedValue([]);
    const { result } = renderHook(() => useAgentJobs());
    expect(result.current.jobs).toEqual([]);
  });

  it("calls getAgentJobs on mount", async () => {
    mockedGetAgentJobs.mockResolvedValue([]);
    renderHook(() => useAgentJobs());
    await waitFor(() => {
      expect(mockedGetAgentJobs).toHaveBeenCalledTimes(1);
    });
  });
});
