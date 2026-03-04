import type { Notification, TaskCreatePayload, ServiceStatus } from "./notificationTypes";
import { apiFetch } from "./api";

export function getNotifications(limit = 50, status?: string) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (status) params.set("status", status);
  return apiFetch<{ notifications: Notification[] }>(`/api/notifications?${params}`);
}

export function replyToNotification(
  notificationId: string,
  body: string,
  source: string,
  sourceAccount: string,
  sourceId: string,
) {
  return apiFetch(`/api/notifications/${notificationId}/action`, {
    method: "POST",
    body: JSON.stringify({
      notification_id: notificationId,
      action: "reply",
      payload: { body, source, source_account: sourceAccount, source_id: sourceId },
    }),
  });
}

export function archiveNotification(notificationId: string) {
  return apiFetch(`/api/notifications/${notificationId}/action`, {
    method: "POST",
    body: JSON.stringify({ notification_id: notificationId, action: "archive" }),
  });
}

export function markNotificationRead(notificationId: string) {
  return apiFetch(`/api/notifications/${notificationId}/action`, {
    method: "POST",
    body: JSON.stringify({ notification_id: notificationId, action: "mark_read" }),
  });
}

export function snoozeNotification(notificationId: string, minutes = 30) {
  return apiFetch(`/api/notifications/${notificationId}/action`, {
    method: "POST",
    body: JSON.stringify({
      notification_id: notificationId,
      action: "snooze",
      payload: { snooze_minutes: minutes },
    }),
  });
}

export function createTask(task: TaskCreatePayload) {
  return apiFetch("/api/tasks", {
    method: "POST",
    body: JSON.stringify(task),
  });
}

export function getServiceStatuses() {
  return apiFetch<{ services: ServiceStatus[] }>("/api/services/status");
}

export function getAuthStatus() {
  return apiFetch<{
    gmail_accounts: { email: string; connected: boolean }[];
    outlook_accounts: { email: string; connected: boolean }[];
  }>("/api/auth/status");
}

export function removeGmailAccount(email: string) {
  return apiFetch(`/api/auth/gmail/${encodeURIComponent(email)}`, { method: "DELETE" });
}

export function removeOutlookAccount(email: string) {
  return apiFetch(`/api/auth/outlook/${encodeURIComponent(email)}`, { method: "DELETE" });
}
