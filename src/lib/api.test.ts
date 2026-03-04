import { describe, it, expect, vi, beforeEach } from "vitest";
import { getTriageItems, snoozeItem, dismissItem, createIssue, getStatus } from "./api";

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
