import type { Notification, TaskCreatePayload, ServiceStatus } from "./notificationTypes";
import { apiFetch } from "./api";

export function getNotifications(limit = 50, status?: string, offset = 0) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (status) params.set("status", status);
  return apiFetch<{ notifications: Notification[]; offset: number; has_more: boolean }>(`/api/notifications?${params}`);
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

export function actionNotification(notificationId: string) {
  return apiFetch(`/api/notifications/${notificationId}/action`, {
    method: "POST",
    body: JSON.stringify({ notification_id: notificationId, action: "actioned" }),
  });
}

export function syncEmails() {
  return apiFetch<{ synced: number; errors: string[] }>("/api/sync", {
    method: "POST",
  });
}

export function searchNotifications(query: string, limit = 50, offset = 0) {
  const params = new URLSearchParams({ q: query, limit: String(limit), offset: String(offset) });
  return apiFetch<{ notifications: Notification[]; query: string }>(`/api/notifications/search?${params}`);
}
