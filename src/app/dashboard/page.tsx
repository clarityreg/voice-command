"use client";

import { useEffect, useState } from "react";
import { getTriageItems, type TriageItem } from "@/lib/api";
import { SEVERITY_CONFIG } from "@/lib/severity";

const statusBadge: Record<string, string> = {
  pending: "bg-status-pending/40 text-bark",
  snoozed: "bg-status-snoozed/40 text-bark",
  dismissed: "bg-status-dismissed/40 text-bark",
  actioned: "bg-status-actioned/40 text-bark",
};

const sourceIcon: Record<string, string> = {
  posthog: "\uD83D\uDCCA",
  aikido: "\uD83D\uDEE1\uFE0F",
};

export default function DashboardPage() {
  const [items, setItems] = useState<TriageItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTriageItems()
      .then(setItems)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="py-20 text-center text-bark-muted">Loading events...</div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="py-20 text-center text-bark-muted">
        No events yet. Send a webhook to get started.
      </div>
    );
  }

  return (
    <div>
      <h2 className="mb-4 text-xl font-bold text-bark">All Events</h2>
      <div className="flex flex-col gap-3">
        {items.map((item) => (
          <div
            key={item.id}
            className="rounded-card bg-card-bg p-4 shadow-card"
          >
            <div className="mb-2 flex items-start justify-between">
              <div className="flex items-center gap-2">
                <span className="text-lg">
                  {sourceIcon[item.source] ?? "\uD83D\uDCE6"}
                </span>
                <h3 className="font-medium text-bark line-clamp-1">
                  {item.title}
                </h3>
              </div>
              <span className="shrink-0 text-xs text-bark-light">
                {item.occurrence_count}x
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={`rounded-pill px-2 py-0.5 text-xs font-bold uppercase ${(SEVERITY_CONFIG[item.severity as keyof typeof SEVERITY_CONFIG] ?? SEVERITY_CONFIG.low).badgeBg}`}
              >
                {item.severity}
              </span>
              <span
                className={`rounded-pill px-2 py-0.5 text-xs font-medium ${statusBadge[item.status] ?? ""}`}
              >
                {item.status}
              </span>
              <span className="ml-auto text-xs text-bark-light">
                {new Date(item.last_seen).toLocaleDateString()}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
