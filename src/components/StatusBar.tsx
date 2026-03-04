"use client";

import { useEffect, useState } from "react";
import { getStatus, type TriageStatus } from "@/lib/api";

export default function StatusBar() {
  const [status, setStatus] = useState<TriageStatus | null>(null);

  useEffect(() => {
    getStatus().then(setStatus).catch(() => {});
    const interval = setInterval(() => {
      getStatus().then(setStatus).catch(() => {});
    }, 30_000);
    return () => clearInterval(interval);
  }, []);

  if (!status) {
    return (
      <div className="grid grid-cols-2 gap-3">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-20 animate-pulse rounded-card bg-cream-dark"
          />
        ))}
      </div>
    );
  }

  const metrics = [
    {
      icon: "\uD83D\uDD34",
      value: status.critical_count,
      label: "Critical",
      bg: "bg-sev-critical/30",
    },
    {
      icon: "\uD83D\uDEE1\uFE0F",
      value: status.vulnerability_count,
      label: "Vulns",
      bg: "bg-sev-high/30",
    },
    {
      icon: "\u2705",
      value: status.actioned_today,
      label: "Actioned",
      bg: "bg-sev-low/30",
    },
    {
      icon: "\u23F3",
      value: status.pending_count,
      label: "Pending",
      bg: "bg-sev-medium/30",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3">
      {metrics.map((m) => (
        <div
          key={m.label}
          className={`flex items-center gap-3 rounded-card p-4 shadow-card ${m.bg}`}
        >
          <span className="text-2xl">{m.icon}</span>
          <div>
            <p className="text-xl font-bold text-bark">{m.value}</p>
            <p className="text-xs text-bark-muted">{m.label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
