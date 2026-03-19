export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8070";

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export interface TriageItem {
  id: number;
  source: "posthog" | "aikido";
  title: string;
  description: string;
  severity: "low" | "medium" | "high" | "critical";
  status: "pending" | "snoozed" | "dismissed" | "actioned";
  fingerprint: string;
  occurrence_count: number;
  first_seen: string;
  last_seen: string;
  metadata: Record<string, unknown>;
  recurring?: boolean;
}

export interface TriageStatus {
  critical_count: number;
  vulnerability_count: number;
  actioned_today: number;
  pending_count: number;
}

export function getTriageItems(status?: TriageItem["status"]): Promise<TriageItem[]> {
  const params = status ? `?status=${status}` : "";
  return apiFetch<TriageItem[]>(`/api/triage${params}`);
}

export function snoozeItem(id: number): Promise<TriageItem> {
  return apiFetch<TriageItem>(`/api/triage/${id}/snooze`, { method: "POST" });
}

export function dismissItem(id: number, reason = ""): Promise<TriageItem> {
  return apiFetch<TriageItem>(`/api/triage/${id}/dismiss`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function createIssue(id: number): Promise<Record<string, unknown>> {
  return apiFetch(`/api/triage/${id}/create-issue`, { method: "POST" });
}

export function getStatus(): Promise<TriageStatus> {
  return apiFetch<TriageStatus>("/api/status");
}

export interface MorningBrief {
  new_errors_24h: number;
  new_vulns_24h: number;
  actioned_yesterday: number;
  pending_total: number;
  top_severity: string | null;
  overdue_reviews: number | null;
  pending_email_actions: number | null;
  approaching_deadlines: string[] | null;
  clarity_available: boolean;
}

export function getMorningBrief(): Promise<MorningBrief> {
  return apiFetch<MorningBrief>("/api/brief/morning");
}

export interface AppSettings {
  plane_api_key: string;
  plane_workspace_slug: string;
  plane_project_id: string;
  aikido_webhook_secret: string;
  posthog_api_key: string;
  posthog_project_id: string;
  posthog_host: string;
  openai_api_key?: string;
  stt_backend?: string;
  focus_minutes: number;
  break_minutes: number;
  clarity_api_url?: string;
  clarity_api_key?: string;
  clarity_webhook_secret?: string;
}

export function getSettings(): Promise<AppSettings> {
  return apiFetch<AppSettings>("/api/settings");
}

export function updateSettings(data: Partial<AppSettings>): Promise<AppSettings> {
  return apiFetch<AppSettings>("/api/settings", {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export interface InvestigationResult {
  root_cause: string;
  affected_files: string[];
  suggested_fix: string;
  raw_response: string;
}

export function investigateItem(id: number): Promise<{ item_id: number; investigation: InvestigationResult }> {
  return apiFetch(`/api/triage/${id}/investigate`, { method: "POST" });
}

export interface VoiceResponse {
  intent: { type: string; confidence: number; params: Record<string, unknown> };
  response: string;
  data: Record<string, unknown>;
}

export function processVoice(text: string): Promise<VoiceResponse> {
  return apiFetch<VoiceResponse>("/api/voice/process", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export interface TrendPoint {
  date: string;
  count: number;
}

export interface StatsData {
  weekly_resolved: number;
  avg_triage_hours: number | null;
  trend: TrendPoint[];
  severity_breakdown: Record<string, number>;
}

export function getStats(): Promise<StatsData> {
  return apiFetch<StatsData>("/api/stats");
}

export type AgentJobStatus = "planning" | "plan_ready" | "approved" | "running" | "completed" | "failed" | "cancelled";

export interface AgentEvent {
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface AgentJob {
  id: string;
  triage_item_id: number;
  status: AgentJobStatus;
  plan_text: string | null;
  result_summary: string | null;
  branch_name: string | null;
  error_message: string | null;
  events_json: string;
  created_at: string;
  updated_at: string;
}

export function startAgentFix(itemId: number): Promise<{ job_id: string; status: string }> {
  return apiFetch(`/api/triage/${itemId}/agent-fix`, { method: "POST" });
}

export function getAgentJobs(): Promise<AgentJob[]> {
  return apiFetch<AgentJob[]>("/api/agent/jobs");
}

export function getAgentJob(jobId: string): Promise<AgentJob> {
  return apiFetch<AgentJob>(`/api/agent/jobs/${jobId}`);
}

export function approveAgentPlan(jobId: string): Promise<AgentJob> {
  return apiFetch<AgentJob>(`/api/agent/jobs/${jobId}/approve`, { method: "POST" });
}

export function cancelAgentJob(jobId: string): Promise<AgentJob> {
  return apiFetch<AgentJob>(`/api/agent/jobs/${jobId}/cancel`, { method: "POST" });
}

// --- Plane task management ---

export interface PendingAction {
  action_type: "create_task" | "complete_task";
  project_id: string;
  project_name: string;
  title?: string;
  priority?: string;
  task_ref?: string;
  issue_id?: string;
  state_id?: string;
  sequence_id?: number;
}

export interface PlaneProjectEntry {
  id: string;
  name: string;
  identifier: string;
}

export function confirmPlaneAction(action: PendingAction): Promise<{ response: string }> {
  return apiFetch("/api/plane/confirm-action", {
    method: "POST",
    body: JSON.stringify(action),
  });
}

export function getPlaneProjects(): Promise<{ projects: Record<string, PlaneProjectEntry> }> {
  return apiFetch("/api/plane/projects");
}

export function syncPlaneProjects(): Promise<{ projects: Record<string, PlaneProjectEntry>; error?: string }> {
  return apiFetch("/api/settings/plane/sync-projects", { method: "POST" });
}

export function updateProjectAlias(
  oldAlias: string,
  body: { new_alias: string; id?: string; name?: string; identifier?: string },
): Promise<{ projects: Record<string, PlaneProjectEntry>; error?: string }> {
  return apiFetch(`/api/settings/plane/projects/${encodeURIComponent(oldAlias)}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteProjectAlias(
  alias: string,
): Promise<{ projects: Record<string, PlaneProjectEntry> }> {
  return apiFetch(`/api/settings/plane/projects/${encodeURIComponent(alias)}`, {
    method: "DELETE",
  });
}

export function processAudio(audioBlob: Blob): Promise<VoiceResponse> {
  const form = new FormData();
  form.append("audio", audioBlob, "audio.webm");
  return fetch(`${API_BASE}/api/voice/process-audio`, {
    method: "POST",
    body: form,
  }).then(async (res) => {
    if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
    return res.json() as Promise<VoiceResponse>;
  });
}
