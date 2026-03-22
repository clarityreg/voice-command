import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

// Mock wsClient before importing the hook
const mockConnect = vi.fn();
const mockDisconnect = vi.fn();
let capturedCallbacks: Record<string, (...args: unknown[]) => void> = {};

vi.mock("@/lib/wsClient", () => ({
  createWsClient: vi.fn((cbs: Record<string, (...args: unknown[]) => void>) => {
    capturedCallbacks = cbs;
    return { connect: mockConnect, disconnect: mockDisconnect };
  }),
}));

import { useNotifications } from "./useNotifications";
import type { Notification, ServiceStatus } from "@/lib/notificationTypes";

function makeNotification(overrides: Partial<Notification> = {}): Notification {
  return {
    id: "n1",
    source: "gmail",
    source_account: "test@gmail.com",
    source_id: "src-1",
    notification_type: "email",
    title: "Test Email",
    body: "Hello world",
    sender_name: "Alice",
    timestamp: "2026-03-06T12:00:00Z",
    priority: "normal",
    triage_status: "unread",
    is_actionable: true,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  capturedCallbacks = {};
});

describe("useNotifications", () => {
  it("connects WebSocket on mount and disconnects on unmount", () => {
    const { unmount } = renderHook(() => useNotifications());
    expect(mockConnect).toHaveBeenCalledOnce();
    unmount();
    expect(mockDisconnect).toHaveBeenCalledOnce();
  });

  it("loads initial notifications via onInitialLoad", () => {
    const { result } = renderHook(() => useNotifications());
    const items = [makeNotification({ id: "n1" }), makeNotification({ id: "n2" })];

    act(() => capturedCallbacks.onInitialLoad?.(items));

    expect(result.current.allNotifications).toHaveLength(2);
  });

  it("adds new notification via onNewNotification", () => {
    const { result } = renderHook(() => useNotifications());

    act(() => capturedCallbacks.onInitialLoad?.([]));
    act(() => capturedCallbacks.onNewNotification?.(makeNotification({ id: "new-1" })));

    expect(result.current.allNotifications).toHaveLength(1);
    expect(result.current.allNotifications[0].id).toBe("new-1");
  });

  it("updates existing notification by source+source_id match", () => {
    const { result } = renderHook(() => useNotifications());
    const original = makeNotification({ id: "n1", source: "slack", source_id: "s1", title: "Old" });

    act(() => capturedCallbacks.onInitialLoad?.([original]));
    act(() =>
      capturedCallbacks.onNewNotification?.(
        makeNotification({ id: "n1-updated", source: "slack", source_id: "s1", title: "New" }),
      ),
    );

    expect(result.current.allNotifications).toHaveLength(1);
    expect(result.current.allNotifications[0].title).toBe("New");
  });

  it("updates notification via onNotificationUpdated", () => {
    const { result } = renderHook(() => useNotifications());

    act(() => capturedCallbacks.onInitialLoad?.([makeNotification({ id: "n1", title: "Before" })]));
    act(() => capturedCallbacks.onNotificationUpdated?.("n1", { title: "After" }));

    expect(result.current.allNotifications[0].title).toBe("After");
  });

  it("removes notification via onNotificationRemoved", () => {
    const { result } = renderHook(() => useNotifications());

    act(() => capturedCallbacks.onInitialLoad?.([makeNotification({ id: "n1" })]));
    act(() => capturedCallbacks.onNotificationRemoved?.("n1"));

    expect(result.current.allNotifications).toHaveLength(0);
  });

  it("tracks connection status", () => {
    const { result } = renderHook(() => useNotifications());

    expect(result.current.connected).toBe(false);
    act(() => capturedCallbacks.onConnected?.());
    expect(result.current.connected).toBe(true);
    act(() => capturedCallbacks.onDisconnected?.());
    expect(result.current.connected).toBe(false);
  });

  it("tracks service statuses", () => {
    const { result } = renderHook(() => useNotifications());
    const status: ServiceStatus = { service: "posthog", connected: true, account: "PostHog" };

    act(() => capturedCallbacks.onConnectionStatus?.(status));

    expect(result.current.serviceStatuses).toHaveLength(1);
    expect(result.current.serviceStatuses[0].service).toBe("posthog");
  });

  it("updates existing service status instead of duplicating", () => {
    const { result } = renderHook(() => useNotifications());

    act(() =>
      capturedCallbacks.onConnectionStatus?.({ service: "slack", connected: true, account: "ws1" }),
    );
    act(() =>
      capturedCallbacks.onConnectionStatus?.({ service: "slack", connected: false, account: "ws1" }),
    );

    expect(result.current.serviceStatuses).toHaveLength(1);
    expect(result.current.serviceStatuses[0].connected).toBe(false);
  });

  // --- Filtering ---

  it("filters out archived notifications", () => {
    const { result } = renderHook(() => useNotifications());

    act(() =>
      capturedCallbacks.onInitialLoad?.([
        makeNotification({ id: "n1", triage_status: "unread" }),
        makeNotification({ id: "n2", triage_status: "archived" }),
      ]),
    );

    expect(result.current.notifications).toHaveLength(1);
    expect(result.current.notifications[0].id).toBe("n1");
  });

  it("filters by source when activeFilter is set", () => {
    const { result } = renderHook(() => useNotifications());

    act(() =>
      capturedCallbacks.onInitialLoad?.([
        makeNotification({ id: "n1", source: "gmail" }),
        makeNotification({ id: "n2", source: "slack" }),
      ]),
    );

    act(() => result.current.setActiveFilter("gmail"));

    expect(result.current.notifications).toHaveLength(1);
    expect(result.current.notifications[0].source).toBe("gmail");
  });

  it("filters by search query across title, body, and sender", () => {
    const { result } = renderHook(() => useNotifications());

    act(() =>
      capturedCallbacks.onInitialLoad?.([
        makeNotification({ id: "n1", title: "Bug Report", body: "app crashes", sender_name: "Bob" }),
        makeNotification({ id: "n2", title: "Meeting", body: "standup", sender_name: "Alice" }),
      ]),
    );

    act(() => result.current.setSearchQuery("crash"));

    expect(result.current.notifications).toHaveLength(1);
    expect(result.current.notifications[0].id).toBe("n1");
  });

  // --- Sorting ---

  it("sorts by priority first, then timestamp", () => {
    const { result } = renderHook(() => useNotifications());

    act(() =>
      capturedCallbacks.onInitialLoad?.([
        makeNotification({ id: "low", priority: "low", timestamp: "2026-03-06T14:00:00Z" }),
        makeNotification({ id: "urgent", priority: "urgent", timestamp: "2026-03-06T12:00:00Z" }),
        makeNotification({ id: "normal", priority: "normal", timestamp: "2026-03-06T13:00:00Z" }),
      ]),
    );

    expect(result.current.notifications.map((n) => n.id)).toEqual(["urgent", "normal", "low"]);
  });

  // --- Unread counts ---

  it("computes unread counts per source", () => {
    const { result } = renderHook(() => useNotifications());

    act(() =>
      capturedCallbacks.onInitialLoad?.([
        makeNotification({ id: "n1", source: "gmail", triage_status: "unread" }),
        makeNotification({ id: "n2", source: "gmail", triage_status: "read" }),
        makeNotification({ id: "n3", source: "slack", triage_status: "unread" }),
        makeNotification({ id: "n4", source: "posthog", triage_status: "unread" }),
      ]),
    );

    expect(result.current.unreadCounts.gmail).toBe(1);
    expect(result.current.unreadCounts.slack).toBe(1);
    expect(result.current.unreadCounts.posthog).toBe(1);
    expect(result.current.unreadCounts.total).toBe(3);
  });

  // --- Actions ---

  it("markRead dispatches UPDATE_ONE with read status", () => {
    const { result } = renderHook(() => useNotifications());

    act(() => capturedCallbacks.onInitialLoad?.([makeNotification({ id: "n1", triage_status: "unread" })]));
    act(() => result.current.markRead("n1"));

    expect(result.current.allNotifications[0].triage_status).toBe("read");
  });

  it("archive dispatches UPDATE_ONE with archived status", () => {
    const { result } = renderHook(() => useNotifications());

    act(() => capturedCallbacks.onInitialLoad?.([makeNotification({ id: "n1" })]));
    act(() => result.current.archive("n1"));

    expect(result.current.allNotifications[0].triage_status).toBe("archived");
    // Archived items are filtered out of the main list
    expect(result.current.notifications).toHaveLength(0);
  });

  // --- Selection ---

  it("selectedNotification tracks by setSelectedId", () => {
    const { result } = renderHook(() => useNotifications());

    act(() => capturedCallbacks.onInitialLoad?.([makeNotification({ id: "n1" })]));

    expect(result.current.selectedNotification).toBeNull();
    act(() => result.current.setSelectedId("n1"));
    expect(result.current.selectedNotification?.id).toBe("n1");
  });
});
