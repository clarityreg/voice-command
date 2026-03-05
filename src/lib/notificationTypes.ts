export type Source = "gmail" | "outlook" | "slack" | "asana" | "plane";

export const SOURCES: (Source | "all")[] = ["all", "gmail", "outlook", "slack", "asana", "plane"];
export type NotificationType = "email" | "message" | "task_update" | "task_assigned" | "mention" | "comment" | "reminder";
export type Priority = "urgent" | "high" | "normal" | "low";
export type NotificationTriageStatus = "unread" | "read" | "snoozed" | "archived" | "actioned";

export interface Notification {
  id: string;
  source: Source;
  source_account: string;
  source_id: string;
  notification_type: NotificationType;
  title: string;
  body: string;
  sender_name: string;
  sender_avatar?: string;
  timestamp: string;
  priority: Priority;
  triage_status: NotificationTriageStatus;
  is_actionable: boolean;
  thread_id?: string;
  channel_name?: string;
  project_name?: string;
  snoozed_until?: string;
  raw_payload?: Record<string, unknown>;
}

export interface WebSocketMessage {
  event: "new_notification" | "notification_updated" | "notification_removed" | "connection_status" | "error" | "initial_load"
    | "agent_job_created" | "agent_progress" | "agent_plan_ready" | "agent_job_updated" | "agent_completed" | "agent_failed";
  data: Record<string, unknown>;
}

export interface ServiceStatus {
  service: string;
  connected: boolean;
  account: string;
}

export interface TaskCreatePayload {
  title: string;
  description?: string;
  target: "plane" | "asana";
  priority?: Priority;
  project_id?: string;
  source_notification_id?: string;
}

export const SOURCE_CONFIG: Record<Source, { label: string; color: string; icon: string }> = {
  gmail: { label: "Gmail", color: "#DC2626", icon: "✉️" },
  outlook: { label: "Outlook", color: "#0066CC", icon: "📧" },
  slack: { label: "Slack", color: "#611F69", icon: "💬" },
  asana: { label: "Asana", color: "#E8573A", icon: "📋" },
  plane: { label: "Plane", color: "#2563EB", icon: "✈️" },
};

export const PRIORITY_CONFIG: Record<Priority, { label: string; color: string }> = {
  urgent: { label: "Urgent", color: "#DC2626" },
  high: { label: "High", color: "#EA580C" },
  normal: { label: "Normal", color: "#4B5563" },
  low: { label: "Low", color: "#6B7280" },
};
