"use client";

import type { TriageItem } from "@/lib/api";
import { SEVERITY_CONFIG, SOURCE_BADGE } from "@/lib/severity";

interface TriageCardProps {
  item: TriageItem;
  onSnooze: (id: number) => void;
  onDismiss: (id: number) => void;
  onCreateIssue: (id: number) => void;
  onInvestigate?: (id: number) => void;
  investigating?: boolean;
  onFix?: (id: number) => void;
  fixing?: boolean;
}

export default function TriageCard({
  item,
  onSnooze,
  onDismiss,
  onCreateIssue,
  onInvestigate,
  investigating,
  onFix,
  fixing,
}: TriageCardProps) {
  const sev = SEVERITY_CONFIG[item.severity as keyof typeof SEVERITY_CONFIG] ?? SEVERITY_CONFIG.low;

  return (
    <div className={`rounded-card p-6 shadow-card ${sev.bg}`}>
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`rounded-pill px-2.5 py-0.5 text-xs font-medium ${SOURCE_BADGE[item.source] ?? "bg-cream-dark text-bark"}`}
          >
            {item.source}
          </span>
          <span className="text-base">{sev.icon}</span>
          <span
            className={`rounded-pill px-2.5 py-0.5 text-xs font-bold uppercase ${sev.badgeBg}`}
          >
            {item.severity}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {item.recurring && (
            <span className="rounded-pill bg-accent/30 px-2 py-0.5 text-xs font-bold text-accent">
              Recurring
            </span>
          )}
          {item.occurrence_count > 1 && (
            <span className="text-sm text-bark-muted">
              {item.occurrence_count}x
            </span>
          )}
        </div>
      </div>

      <h2 className="mb-2 text-lg font-semibold text-bark">{item.title}</h2>

      {item.description && (
        <p className="mb-4 text-sm text-bark-muted">{item.description}</p>
      )}

      <div className="mb-4 flex gap-4 text-xs text-bark-light">
        <span>First seen: {new Date(item.first_seen).toLocaleString()}</span>
        <span>Last seen: {new Date(item.last_seen).toLocaleString()}</span>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => onCreateIssue(item.id)}
          className="rounded-pill bg-nav-bg px-4 py-2 text-sm font-medium text-cream transition hover:opacity-90"
        >
          Create Issue
        </button>
        {onInvestigate && (
          <button
            onClick={() => onInvestigate(item.id)}
            disabled={investigating}
            className="rounded-pill bg-accent/20 px-4 py-2 text-sm font-medium text-accent transition hover:bg-accent/30 disabled:opacity-50"
          >
            {investigating ? "Investigating..." : "Investigate"}
          </button>
        )}
        {onFix && (
          <button
            onClick={() => onFix(item.id)}
            disabled={fixing}
            className="rounded-pill bg-accent/20 px-3 py-1 text-sm font-medium text-accent transition hover:bg-accent/30 disabled:opacity-50"
          >
            {fixing ? "Fixing..." : "Fix with Claude"}
          </button>
        )}
        <button
          onClick={() => onSnooze(item.id)}
          className="rounded-pill bg-cream px-4 py-2 text-sm font-medium text-bark transition hover:bg-cream-dark"
        >
          Snooze
        </button>
        <button
          onClick={() => onDismiss(item.id)}
          className="rounded-pill bg-cream px-4 py-2 text-sm font-medium text-bark transition hover:bg-cream-dark"
        >
          Dismiss
        </button>
      </div>
    </div>
  );
}
