import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getTriageItems, snoozeItem, dismissItem, createIssue, getStatus,
  getMorningBrief, getSettings, updateSettings, investigateItem,
  processVoice, getStats, startAgentFix, getAgentJobs, getAgentJob,
  approveAgentPlan, cancelAgentJob, confirmPlaneAction, getPlaneProjects,
  syncPlaneProjects, updateProjectAlias, deleteProjectAlias, processAudio,
} from "./api";

const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

function okResponse(data: unknown) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(data),
  } as Response);
}

function errorResponse(status: number, body: string) {
  return Promise.resolve({
    ok: false,
    status,
    text: () => Promise.resolve(body),
  } as Response);
}

describe("getTriageItems", () => {
  it("fetches all items when no status filter", async () => {
    mockFetch.mockReturnValueOnce(okResponse([]));
    const result = await getTriageItems();
    expect(result).toEqual([]);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/triage",
      expect.objectContaining({ headers: { "Content-Type": "application/json" } }),
    );
  });

  it("appends status query param when provided", async () => {
    mockFetch.mockReturnValueOnce(okResponse([]));
    await getTriageItems("pending");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/triage?status=pending",
      expect.any(Object),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockReturnValueOnce(errorResponse(500, "Internal Server Error"));
    await expect(getTriageItems()).rejects.toThrow("API error 500");
  });
});

describe("snoozeItem", () => {
  it("posts to the snooze endpoint", async () => {
    const item = { id: 1, status: "snoozed" };
    mockFetch.mockReturnValueOnce(okResponse(item));
    const result = await snoozeItem(1);
    expect(result).toEqual(item);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/triage/1/snooze",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

describe("dismissItem", () => {
  it("posts to the dismiss endpoint with reason", async () => {
    const item = { id: 2, status: "dismissed" };
    mockFetch.mockReturnValueOnce(okResponse(item));
    const result = await dismissItem(2, "not relevant");
    expect(result).toEqual(item);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/triage/2/dismiss",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ reason: "not relevant" }),
      }),
    );
  });
});

describe("createIssue", () => {
  it("posts to the create-issue endpoint", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ issue_url: "https://example.com" }));
    const result = await createIssue(3);
    expect(result).toEqual({ issue_url: "https://example.com" });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/triage/3/create-issue",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

describe("getStatus", () => {
  it("fetches the status endpoint", async () => {
    const status = { critical_count: 1, vulnerability_count: 2, actioned_today: 3, pending_count: 4 };
    mockFetch.mockReturnValueOnce(okResponse(status));
    const result = await getStatus();
    expect(result).toEqual(status);
  });
});

describe("getMorningBrief", () => {
  it("fetches morning brief", async () => {
    const brief = { new_errors_24h: 5, new_vulns_24h: 1, actioned_yesterday: 3, pending_total: 10, top_severity: "high" };
    mockFetch.mockReturnValueOnce(okResponse(brief));
    const result = await getMorningBrief();
    expect(result).toEqual(brief);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/brief/morning",
      expect.any(Object),
    );
  });
});

describe("getSettings", () => {
  it("fetches settings", async () => {
    const settings = { plane_api_key: "k", focus_minutes: 25, break_minutes: 5 };
    mockFetch.mockReturnValueOnce(okResponse(settings));
    const result = await getSettings();
    expect(result).toEqual(settings);
  });
});

describe("updateSettings", () => {
  it("puts partial settings", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ focus_minutes: 30 }));
    await updateSettings({ focus_minutes: 30 });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/settings",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ focus_minutes: 30 }),
      }),
    );
  });
});

describe("investigateItem", () => {
  it("posts to investigate endpoint", async () => {
    const data = { item_id: 1, investigation: { root_cause: "bug", affected_files: [], suggested_fix: "fix it", raw_response: "" } };
    mockFetch.mockReturnValueOnce(okResponse(data));
    const result = await investigateItem(1);
    expect(result).toEqual(data);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/triage/1/investigate",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

describe("processVoice", () => {
  it("posts text for voice processing", async () => {
    const resp = { intent: { type: "greeting", confidence: 0.9, params: {} }, response: "Hello!", data: {} };
    mockFetch.mockReturnValueOnce(okResponse(resp));
    const result = await processVoice("hello");
    expect(result).toEqual(resp);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/voice/process",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ text: "hello" }),
      }),
    );
  });
});

describe("getStats", () => {
  it("fetches stats", async () => {
    const stats = { weekly_resolved: 10, avg_triage_hours: 2.5, trend: [], severity_breakdown: {} };
    mockFetch.mockReturnValueOnce(okResponse(stats));
    const result = await getStats();
    expect(result).toEqual(stats);
  });
});

describe("agent functions", () => {
  it("startAgentFix posts to agent-fix endpoint", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ job_id: "j1", status: "planning" }));
    const result = await startAgentFix(1);
    expect(result).toEqual({ job_id: "j1", status: "planning" });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/triage/1/agent-fix",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("getAgentJobs fetches all jobs", async () => {
    mockFetch.mockReturnValueOnce(okResponse([]));
    const result = await getAgentJobs();
    expect(result).toEqual([]);
  });

  it("getAgentJob fetches a specific job", async () => {
    const job = { id: "j1", status: "completed" };
    mockFetch.mockReturnValueOnce(okResponse(job));
    const result = await getAgentJob("j1");
    expect(result).toEqual(job);
  });

  it("approveAgentPlan posts to approve endpoint", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ id: "j1", status: "approved" }));
    await approveAgentPlan("j1");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/agent/jobs/j1/approve",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("cancelAgentJob posts to cancel endpoint", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ id: "j1", status: "cancelled" }));
    await cancelAgentJob("j1");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/agent/jobs/j1/cancel",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

describe("Plane functions", () => {
  it("confirmPlaneAction posts action", async () => {
    const action = { action_type: "create_task" as const, project_id: "p1", project_name: "Test", title: "New task" };
    mockFetch.mockReturnValueOnce(okResponse({ response: "Done" }));
    const result = await confirmPlaneAction(action);
    expect(result).toEqual({ response: "Done" });
  });

  it("getPlaneProjects fetches projects", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ projects: {} }));
    const result = await getPlaneProjects();
    expect(result).toEqual({ projects: {} });
  });

  it("syncPlaneProjects posts to sync", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ projects: {} }));
    await syncPlaneProjects();
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/settings/plane/sync-projects",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("updateProjectAlias puts with encoded alias", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ projects: {} }));
    await updateProjectAlias("old name", { new_alias: "new name" });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/settings/plane/projects/old%20name",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ new_alias: "new name" }),
      }),
    );
  });

  it("deleteProjectAlias deletes with encoded alias", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ projects: {} }));
    await deleteProjectAlias("my project");
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/settings/plane/projects/my%20project",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});

describe("processAudio", () => {
  it("sends audio blob as FormData", async () => {
    const resp = { intent: { type: "test", confidence: 1, params: {} }, response: "ok", data: {} };
    mockFetch.mockReturnValueOnce(Promise.resolve({
      ok: true,
      json: () => Promise.resolve(resp),
    }));
    const blob = new Blob(["audio"], { type: "audio/webm" });
    const result = await processAudio(blob);
    expect(result).toEqual(resp);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8070/api/voice/process-audio",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockReturnValueOnce(Promise.resolve({
      ok: false,
      status: 400,
      text: () => Promise.resolve("Bad Request"),
    }));
    const blob = new Blob(["audio"], { type: "audio/webm" });
    await expect(processAudio(blob)).rejects.toThrow("API error 400");
  });
});
