import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getNotifications,
  replyToNotification,
  archiveNotification,
  markNotificationRead,
  snoozeNotification,
  createTask,
  getServiceStatuses,
  getAuthStatus,
  removeGmailAccount,
  removeOutlookAccount,
  actionNotification,
  syncEmails,
  searchNotifications,
} from "./notificationApi";

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

describe("getNotifications", () => {
  it("fetches with default params", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ notifications: [], offset: 0, has_more: false }));
    const result = await getNotifications();
    expect(result).toEqual({ notifications: [], offset: 0, has_more: false });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/notifications?limit=50&offset=0"),
      expect.any(Object),
    );
  });

  it("includes status filter when provided", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ notifications: [], offset: 0, has_more: false }));
    await getNotifications(20, "unread", 10);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("limit=20"),
      expect.any(Object),
    );
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("offset=10"),
      expect.any(Object),
    );
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("status=unread"),
      expect.any(Object),
    );
  });
});

describe("replyToNotification", () => {
  it("posts reply with correct payload", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ ok: true }));
    await replyToNotification("n1", "Hello", "gmail", "test@gmail.com", "src-1");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/notifications/n1/action"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          notification_id: "n1",
          action: "reply",
          payload: { body: "Hello", source: "gmail", source_account: "test@gmail.com", source_id: "src-1" },
        }),
      }),
    );
  });
});

describe("archiveNotification", () => {
  it("posts archive action", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ ok: true }));
    await archiveNotification("n2");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/notifications/n2/action"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ notification_id: "n2", action: "archive" }),
      }),
    );
  });
});

describe("markNotificationRead", () => {
  it("posts mark_read action", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ ok: true }));
    await markNotificationRead("n3");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/notifications/n3/action"),
      expect.objectContaining({
        body: JSON.stringify({ notification_id: "n3", action: "mark_read" }),
      }),
    );
  });
});

describe("snoozeNotification", () => {
  it("snoozes with default 30 minutes", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ ok: true }));
    await snoozeNotification("n4");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/notifications/n4/action"),
      expect.objectContaining({
        body: JSON.stringify({
          notification_id: "n4",
          action: "snooze",
          payload: { snooze_minutes: 30 },
        }),
      }),
    );
  });

  it("snoozes with custom minutes", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ ok: true }));
    await snoozeNotification("n4", 60);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/notifications/n4/action"),
      expect.objectContaining({
        body: expect.stringContaining('"snooze_minutes":60'),
      }),
    );
  });
});

describe("createTask", () => {
  it("posts task creation payload", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ id: "t1" }));
    await createTask({ title: "Fix bug", target: "plane", priority: "high" });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/tasks"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ title: "Fix bug", target: "plane", priority: "high" }),
      }),
    );
  });
});

describe("getServiceStatuses", () => {
  it("fetches service statuses", async () => {
    const data = { services: [{ service: "gmail", connected: true, account: "x@gmail.com" }] };
    mockFetch.mockReturnValueOnce(okResponse(data));
    const result = await getServiceStatuses();
    expect(result).toEqual(data);
  });
});

describe("getAuthStatus", () => {
  it("fetches auth status", async () => {
    const data = { gmail_accounts: [], outlook_accounts: [] };
    mockFetch.mockReturnValueOnce(okResponse(data));
    const result = await getAuthStatus();
    expect(result).toEqual(data);
  });
});

describe("removeGmailAccount", () => {
  it("sends delete for encoded email", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ ok: true }));
    await removeGmailAccount("test@gmail.com");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/gmail/test%40gmail.com"),
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});

describe("removeOutlookAccount", () => {
  it("sends delete for outlook account", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ ok: true }));
    await removeOutlookAccount("test@outlook.com");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/outlook/test%40outlook.com"),
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});

describe("actionNotification", () => {
  it("posts actioned action", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ ok: true }));
    await actionNotification("n5");
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/notifications/n5/action"),
      expect.objectContaining({
        body: JSON.stringify({ notification_id: "n5", action: "actioned" }),
      }),
    );
  });
});

describe("syncEmails", () => {
  it("posts to sync endpoint", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ synced: 5, errors: [] }));
    const result = await syncEmails();
    expect(result).toEqual({ synced: 5, errors: [] });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/sync"),
      expect.objectContaining({ method: "POST" }),
    );
  });
});

describe("searchNotifications", () => {
  it("passes query and pagination params", async () => {
    mockFetch.mockReturnValueOnce(okResponse({ notifications: [], query: "test" }));
    await searchNotifications("test", 25, 5);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("q=test"),
      expect.any(Object),
    );
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("limit=25"),
      expect.any(Object),
    );
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("offset=5"),
      expect.any(Object),
    );
  });
});
