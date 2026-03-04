import type { Notification, WebSocketMessage, ServiceStatus } from "./notificationTypes";
import { API_BASE } from "./api";
const WS_BASE = API_BASE.replace(/^http/, "ws");
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_DELAY = 30000;

export type WsCallback = {
  onInitialLoad?: (notifications: Notification[]) => void;
  onNewNotification?: (notification: Notification) => void;
  onNotificationUpdated?: (id: string, updates: Partial<Notification>) => void;
  onNotificationRemoved?: (id: string) => void;
  onConnectionStatus?: (status: ServiceStatus) => void;
  onAgentJobCreated?: (data: Record<string, unknown>) => void;
  onAgentProgress?: (data: Record<string, unknown>) => void;
  onAgentPlanReady?: (data: Record<string, unknown>) => void;
  onAgentJobUpdated?: (data: Record<string, unknown>) => void;
  onAgentCompleted?: (data: Record<string, unknown>) => void;
  onAgentFailed?: (data: Record<string, unknown>) => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
};

export function createWsClient(callbacks: WsCallback) {
  let ws: WebSocket | null = null;
  let reconnectAttempts = 0;
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  let stopped = false;

  function connect() {
    if (stopped) return;
    if (ws?.readyState === WebSocket.OPEN) return;

    try {
      ws = new WebSocket(`${WS_BASE}/ws`);

      ws.onopen = () => {
        reconnectAttempts = 0;
        callbacks.onConnected?.();
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data as string);
          handleMessage(message);
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        callbacks.onDisconnected?.();
        scheduleReconnect();
      };

      ws.onerror = () => {
        ws?.close();
      };
    } catch {
      scheduleReconnect();
    }
  }

  function handleMessage(message: WebSocketMessage) {
    switch (message.event) {
      case "initial_load": {
        const items = (message.data as { notifications: Notification[] }).notifications;
        callbacks.onInitialLoad?.(items);
        break;
      }
      case "new_notification":
        callbacks.onNewNotification?.(message.data as unknown as Notification);
        break;
      case "notification_updated": {
        const { id, ...updates } = message.data;
        callbacks.onNotificationUpdated?.(id as string, updates as Partial<Notification>);
        break;
      }
      case "notification_removed":
        callbacks.onNotificationRemoved?.((message.data as { id: string }).id);
        break;
      case "connection_status":
        callbacks.onConnectionStatus?.(message.data as unknown as ServiceStatus);
        break;
      case "agent_job_created":
        callbacks.onAgentJobCreated?.(message.data);
        break;
      case "agent_progress":
        callbacks.onAgentProgress?.(message.data);
        break;
      case "agent_plan_ready":
        callbacks.onAgentPlanReady?.(message.data);
        break;
      case "agent_job_updated":
        callbacks.onAgentJobUpdated?.(message.data);
        break;
      case "agent_completed":
        callbacks.onAgentCompleted?.(message.data);
        break;
      case "agent_failed":
        callbacks.onAgentFailed?.(message.data);
        break;
    }
  }

  function scheduleReconnect() {
    if (stopped) return;
    if (reconnectTimeout) clearTimeout(reconnectTimeout);
    const delay = Math.min(RECONNECT_DELAY * Math.pow(1.5, reconnectAttempts), MAX_RECONNECT_DELAY);
    reconnectTimeout = setTimeout(() => {
      reconnectAttempts++;
      connect();
    }, delay);
  }

  function disconnect() {
    stopped = true;
    if (reconnectTimeout) clearTimeout(reconnectTimeout);
    ws?.close();
    ws = null;
  }

  return { connect, disconnect };
}
