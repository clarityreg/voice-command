"use client";

import { useState } from "react";
import type { AgentJob, AgentEvent } from "@/lib/api";
import AgentProgressStream from "./AgentProgressStream";
import AgentPlanReview from "./AgentPlanReview";

interface AgentJobCardProps {
  job: AgentJob;
  events: AgentEvent[];
  onApprove: (id: string) => void;
  onCancel: (id: string) => void;
}

const STATUS_BADGE: Record<string, string> = {
  planning: "bg-blue-100 text-blue-700",
  plan_ready: "bg-yellow-100 text-yellow-700",
  approved: "bg-accent/20 text-accent",
  running: "bg-accent/20 text-accent",
  completed: "bg-sev-low/20 text-sev-low",
  failed: "bg-sev-critical/20 text-sev-critical",
  cancelled: "bg-bark-muted/20 text-bark-muted",
};

function relativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function AgentJobCard({ job, events, onApprove, onCancel }: AgentJobCardProps) {
  const isActive = ["planning", "plan_ready", "approved", "running"].includes(job.status);
  const [expanded, setExpanded] = useState(isActive);

  return (
    <div className="rounded-card bg-nav-bg p-4 shadow-card">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`rounded-pill px-2.5 py-0.5 text-xs font-medium ${STATUS_BADGE[job.status] ?? "bg-cream-dark text-bark"}`}
          >
            {job.status.replace("_", " ")}
          </span>
          <span className="text-sm text-bark-muted">Item #{job.triage_item_id}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-bark-muted">{relativeTime(job.created_at)}</span>
          <button
            onClick={() => setExpanded((e) => !e)}
            className="rounded px-2 py-0.5 text-xs text-bark-muted hover:text-bark"
          >
            {expanded ? "▲" : "▼"}
          </button>
        </div>
      </div>

      {job.branch_name && (
        <p className="mt-1 font-mono text-xs text-bark-muted">{job.branch_name}</p>
      )}

      {expanded && (
        <div className="mt-3 space-y-3">
          {events.length > 0 && <AgentProgressStream events={events} />}

          {job.status === "plan_ready" && job.plan_text && (
            <AgentPlanReview
              planText={job.plan_text}
              onApprove={() => onApprove(job.id)}
              onCancel={() => onCancel(job.id)}
            />
          )}

          {job.plan_text && job.status !== "plan_ready" && (
            <details className="text-sm">
              <summary className="cursor-pointer text-bark-muted hover:text-bark">View plan</summary>
              <pre className="mt-2 whitespace-pre-wrap text-bark-muted">{job.plan_text}</pre>
            </details>
          )}

          {(job.status === "completed" || job.status === "failed") && job.result_summary && (
            <div className="rounded-card bg-cream p-3 text-sm text-bark">
              <span className="font-medium">Result: </span>
              {job.result_summary}
            </div>
          )}

          {job.error_message && (
            <div className="rounded-card bg-sev-critical/10 p-3 text-sm text-sev-critical">
              {job.error_message}
            </div>
          )}

          {isActive && job.status !== "plan_ready" && (
            <div className="flex gap-2">
              <button
                onClick={() => onCancel(job.id)}
                className="rounded-pill bg-cream px-3 py-1.5 text-xs font-medium text-bark transition hover:bg-cream-dark"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
