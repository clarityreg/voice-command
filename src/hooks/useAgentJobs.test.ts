import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useAgentJobs } from "./useAgentJobs";

vi.mock("@/lib/api", () => ({
  getAgentJobs: vi.fn(),
  approveAgentPlan: vi.fn(),
  cancelAgentJob: vi.fn(),
}));

type WsCallbacks = Record<string, (data: Record<string, unknown>) => void>;
let capturedCallbacks: WsCallbacks = {};
const mockConnect = vi.fn();
const mockDisconnect = vi.fn();

vi.mock("@/lib/wsClient", () => ({
  createWsClient: vi.fn((opts: Record<string, unknown>) => {
    capturedCallbacks = opts as unknown as WsCallbacks;
    return { connect: mockConnect, disconnect: mockDisconnect };
  }),
}));

import { getAgentJobs, approveAgentPlan, cancelAgentJob } from "@/lib/api";
const mockedGetAgentJobs = vi.mocked(getAgentJobs);
const mockedApprove = vi.mocked(approveAgentPlan);
const mockedCancel = vi.mocked(cancelAgentJob);

const fakeJob = {
  id: "j1",
  triage_item_id: 1,
  status: "planning" as const,
  plan_text: null,
  result_summary: null,
  branch_name: null,
  error_message: null,
  events_json: "[]",
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
};

beforeEach(() => {
  vi.clearAllMocks();
  capturedCallbacks = {};
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

  it("loads jobs from API", async () => {
    mockedGetAgentJobs.mockResolvedValue([fakeJob]);
    const { result } = renderHook(() => useAgentJobs());
    await waitFor(() => {
      expect(result.current.jobs).toHaveLength(1);
      expect(result.current.loading).toBe(false);
    });
  });

  it("sets error when API fails", async () => {
    mockedGetAgentJobs.mockRejectedValue(new Error("fail"));
    const { result } = renderHook(() => useAgentJobs());
    await waitFor(() => {
      expect(result.current.error).toContain("Could not connect");
      expect(result.current.loading).toBe(false);
    });
  });

  it("connects and disconnects WebSocket", async () => {
    mockedGetAgentJobs.mockResolvedValue([]);
    const { unmount } = renderHook(() => useAgentJobs());
    expect(mockConnect).toHaveBeenCalled();
    unmount();
    expect(mockDisconnect).toHaveBeenCalled();
  });

  it("prepends new job from WebSocket", async () => {
    mockedGetAgentJobs.mockResolvedValue([fakeJob]);
    const { result } = renderHook(() => useAgentJobs());
    await waitFor(() => expect(result.current.jobs).toHaveLength(1));

    const newJob = { ...fakeJob, id: "j2" };
    act(() => {
      capturedCallbacks.onAgentJobCreated(newJob as unknown as Record<string, unknown>);
    });
    expect(result.current.jobs).toHaveLength(2);
    expect(result.current.jobs[0].id).toBe("j2");
  });

  it("updates job from WebSocket events", async () => {
    mockedGetAgentJobs.mockResolvedValue([fakeJob]);
    const { result } = renderHook(() => useAgentJobs());
    await waitFor(() => expect(result.current.jobs).toHaveLength(1));

    const updated = { ...fakeJob, status: "plan_ready" };
    act(() => {
      capturedCallbacks.onAgentPlanReady(updated as unknown as Record<string, unknown>);
    });
    expect(result.current.jobs[0].status).toBe("plan_ready");
  });

  it("appends progress events", async () => {
    mockedGetAgentJobs.mockResolvedValue([fakeJob]);
    const { result } = renderHook(() => useAgentJobs());
    await waitFor(() => expect(result.current.jobs).toHaveLength(1));

    act(() => {
      capturedCallbacks.onAgentProgress({ job_id: "j1", event_type: "assistant", text: "hello" });
    });
    expect(result.current.activeEvents["j1"]).toHaveLength(1);
  });

  it("approve calls API and updates job", async () => {
    mockedGetAgentJobs.mockResolvedValue([fakeJob]);
    const approved = { ...fakeJob, status: "approved" as const };
    mockedApprove.mockResolvedValue(approved);
    const { result } = renderHook(() => useAgentJobs());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.approve("j1");
    });
    expect(mockedApprove).toHaveBeenCalledWith("j1");
    expect(result.current.jobs[0].status).toBe("approved");
  });

  it("cancel calls API and updates job", async () => {
    mockedGetAgentJobs.mockResolvedValue([fakeJob]);
    const cancelled = { ...fakeJob, status: "cancelled" as const };
    mockedCancel.mockResolvedValue(cancelled);
    const { result } = renderHook(() => useAgentJobs());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.cancel("j1");
    });
    expect(mockedCancel).toHaveBeenCalledWith("j1");
    expect(result.current.jobs[0].status).toBe("cancelled");
  });
});
