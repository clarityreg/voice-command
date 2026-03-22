import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createWsClient } from "./wsClient";
import type { WsCallback } from "./wsClient";

// ---------------------------------------------------------------------------
// Minimal WebSocket mock
// ---------------------------------------------------------------------------

class MockWebSocket {
  static OPEN = 1;
  static CLOSED = 3;

  readyState: number;
  url: string;

  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
  });

  // Helper used in tests to simulate server push
  triggerMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  constructor(url: string) {
    this.url = url;
    this.readyState = MockWebSocket.OPEN;
    // Keep reference so tests can grab the latest instance
    MockWebSocket._lastInstance = this;
  }

  static _lastInstance: MockWebSocket | null = null;
}

beforeEach(() => {
  vi.useFakeTimers();
  MockWebSocket._lastInstance = null;
  vi.stubGlobal("WebSocket", MockWebSocket);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// Helper to grab the latest mock WebSocket after connect()
// ---------------------------------------------------------------------------
function getWs(): MockWebSocket {
  const ws = MockWebSocket._lastInstance;
  if (!ws) throw new Error("No WebSocket instance created");
  return ws;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("createWsClient", () => {
  describe("connect", () => {
    it("creates a WebSocket and calls onConnected when open fires", () => {
      const onConnected = vi.fn();
      const client = createWsClient({ onConnected });

      client.connect();
      const ws = getWs();
      ws.onopen?.();

      expect(onConnected).toHaveBeenCalledOnce();
    });

    it("does not create a second WebSocket if already OPEN", () => {
      const onConnected = vi.fn();
      const client = createWsClient({ onConnected });

      client.connect();
      const firstWs = getWs();
      firstWs.onopen?.();

      // Second connect call — readyState is still OPEN
      client.connect();

      expect(onConnected).toHaveBeenCalledOnce();
    });
  });

  describe("disconnect", () => {
    it("closes the socket and stops reconnection", () => {
      const onDisconnected = vi.fn();
      const client = createWsClient({ onDisconnected });

      client.connect();
      const ws = getWs();
      ws.onopen?.();

      client.disconnect();

      expect(ws.close).toHaveBeenCalled();
      // After disconnect, onclose fires but should NOT schedule reconnect
      // Advance timers — no new WS should be created
      MockWebSocket._lastInstance = null;
      vi.advanceTimersByTime(60_000);
      expect(MockWebSocket._lastInstance).toBeNull();
    });

    it("calls onDisconnected when close fires (before explicit disconnect)", () => {
      const onDisconnected = vi.fn();
      const client = createWsClient({ onDisconnected });

      client.connect();
      const ws = getWs();
      ws.onopen?.();
      ws.onclose?.();

      expect(onDisconnected).toHaveBeenCalledOnce();
    });
  });

  describe("reconnection logic", () => {
    it("schedules reconnect after connection drops", () => {
      const onConnected = vi.fn();
      const client = createWsClient({ onConnected });

      client.connect();
      const firstWs = getWs();
      firstWs.onopen?.();

      // Simulate a server-side drop: mark socket closed then fire onclose
      firstWs.readyState = MockWebSocket.CLOSED;
      MockWebSocket._lastInstance = null;
      firstWs.onclose?.();

      // Advance past RECONNECT_DELAY (3000 ms)
      vi.advanceTimersByTime(3_100);

      const secondWs = MockWebSocket._lastInstance;
      expect(secondWs).not.toBeNull();
    });

    it("does not reconnect after explicit disconnect()", () => {
      const client = createWsClient({});

      client.connect();
      const ws = getWs();
      ws.onopen?.();

      client.disconnect();
      MockWebSocket._lastInstance = null;

      vi.advanceTimersByTime(60_000);

      expect(MockWebSocket._lastInstance).toBeNull();
    });

    it("resets reconnect attempts to 0 after successful open", () => {
      const onConnected = vi.fn();
      const client = createWsClient({ onConnected });

      client.connect();
      const ws = getWs();
      ws.onopen?.();

      // Simulate server-side drop: mark closed, clear sentinel, fire onclose
      ws.readyState = MockWebSocket.CLOSED;
      MockWebSocket._lastInstance = null;
      ws.onclose?.();

      // Allow reconnect timer to fire and create new socket
      vi.advanceTimersByTime(3_100);

      const ws2 = getWs();
      ws2.onopen?.();

      // onConnected should now have been called twice (original + after reconnect)
      expect(onConnected).toHaveBeenCalledTimes(2);
    });
  });

  describe("message handling", () => {
    function setupConnectedClient(callbacks: WsCallback) {
      const client = createWsClient(callbacks);
      client.connect();
      const ws = getWs();
      ws.onopen?.();
      return { client, ws };
    }

    it("fires onInitialLoad for initial_load event", () => {
      const onInitialLoad = vi.fn();
      const { ws } = setupConnectedClient({ onInitialLoad });

      const notifications = [{ id: "n1", title: "Hello" }];
      ws.triggerMessage({ event: "initial_load", data: { notifications } });

      expect(onInitialLoad).toHaveBeenCalledWith(notifications);
    });

    it("fires onNewNotification for new_notification event", () => {
      const onNewNotification = vi.fn();
      const { ws } = setupConnectedClient({ onNewNotification });

      const notification = { id: "n2", title: "New" };
      ws.triggerMessage({ event: "new_notification", data: notification });

      expect(onNewNotification).toHaveBeenCalledWith(notification);
    });

    it("fires onNotificationUpdated for notification_updated event", () => {
      const onNotificationUpdated = vi.fn();
      const { ws } = setupConnectedClient({ onNotificationUpdated });

      ws.triggerMessage({ event: "notification_updated", data: { id: "n3", title: "Updated title" } });

      expect(onNotificationUpdated).toHaveBeenCalledWith("n3", { title: "Updated title" });
    });

    it("fires onNotificationRemoved for notification_removed event", () => {
      const onNotificationRemoved = vi.fn();
      const { ws } = setupConnectedClient({ onNotificationRemoved });

      ws.triggerMessage({ event: "notification_removed", data: { id: "n4" } });

      expect(onNotificationRemoved).toHaveBeenCalledWith("n4");
    });

    it("fires onConnectionStatus for connection_status event", () => {
      const onConnectionStatus = vi.fn();
      const { ws } = setupConnectedClient({ onConnectionStatus });

      const status = { service: "gmail", connected: true, account: "test@gmail.com" };
      ws.triggerMessage({ event: "connection_status", data: status });

      expect(onConnectionStatus).toHaveBeenCalledWith(status);
    });

    it("fires onAgentJobCreated for agent_job_created event", () => {
      const onAgentJobCreated = vi.fn();
      const { ws } = setupConnectedClient({ onAgentJobCreated });

      const data = { job_id: "job-1" };
      ws.triggerMessage({ event: "agent_job_created", data });

      expect(onAgentJobCreated).toHaveBeenCalledWith(data);
    });

    it("fires onAgentProgress for agent_progress event", () => {
      const onAgentProgress = vi.fn();
      const { ws } = setupConnectedClient({ onAgentProgress });

      const data = { progress: 50 };
      ws.triggerMessage({ event: "agent_progress", data });

      expect(onAgentProgress).toHaveBeenCalledWith(data);
    });

    it("fires onAgentPlanReady for agent_plan_ready event", () => {
      const onAgentPlanReady = vi.fn();
      const { ws } = setupConnectedClient({ onAgentPlanReady });

      const data = { plan: "do things" };
      ws.triggerMessage({ event: "agent_plan_ready", data });

      expect(onAgentPlanReady).toHaveBeenCalledWith(data);
    });

    it("fires onAgentJobUpdated for agent_job_updated event", () => {
      const onAgentJobUpdated = vi.fn();
      const { ws } = setupConnectedClient({ onAgentJobUpdated });

      const data = { status: "running" };
      ws.triggerMessage({ event: "agent_job_updated", data });

      expect(onAgentJobUpdated).toHaveBeenCalledWith(data);
    });

    it("fires onAgentCompleted for agent_completed event", () => {
      const onAgentCompleted = vi.fn();
      const { ws } = setupConnectedClient({ onAgentCompleted });

      const data = { result: "done" };
      ws.triggerMessage({ event: "agent_completed", data });

      expect(onAgentCompleted).toHaveBeenCalledWith(data);
    });

    it("fires onAgentFailed for agent_failed event", () => {
      const onAgentFailed = vi.fn();
      const { ws } = setupConnectedClient({ onAgentFailed });

      const data = { error: "boom" };
      ws.triggerMessage({ event: "agent_failed", data });

      expect(onAgentFailed).toHaveBeenCalledWith(data);
    });

    it("silently ignores malformed JSON messages", () => {
      const onNewNotification = vi.fn();
      const { ws } = setupConnectedClient({ onNewNotification });

      // Non-JSON string should not throw
      expect(() => {
        ws.onmessage?.({ data: "not-json{{" });
      }).not.toThrow();

      expect(onNewNotification).not.toHaveBeenCalled();
    });
  });

  describe("onerror handler", () => {
    it("closes the socket on error", () => {
      const client = createWsClient({});
      client.connect();
      const ws = getWs();

      ws.onerror?.();

      expect(ws.close).toHaveBeenCalled();
    });
  });
});
