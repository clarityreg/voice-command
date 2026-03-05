"use client";

import { useEffect, useState } from "react";
import { getStats, type StatsData } from "@/lib/api";
import { SEVERITY_CARD_BG, SEVERITY_ICONS, type Severity } from "@/lib/severity";

export default function StatsPage() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch(() => setError("Could not load statistics. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="py-20 text-center text-bark-muted">
        Loading statistics...
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="py-20 text-center">
        <p className="text-sev-critical">{error ?? "Unknown error"}</p>
      </div>
    );
  }

  const maxTrend = Math.max(...stats.trend.map((t) => t.count), 1);

  return (
    <div className="mx-auto max-w-4xl">
      <h2 className="mb-4 text-xl font-bold text-bark">Statistics</h2>

      {/* Summary cards */}
      <div className="mb-6 grid grid-cols-2 gap-3">
        <div className="rounded-card bg-card-bg p-4 shadow-card">
          <p className="text-xs text-bark-muted">Resolved (7d)</p>
          <p className="mt-1 text-2xl font-bold text-bark">
            {stats.weekly_resolved}
          </p>
        </div>
        <div className="rounded-card bg-card-bg p-4 shadow-card">
          <p className="text-xs text-bark-muted">Avg Triage Time</p>
          <p className="mt-1 text-2xl font-bold text-bark">
            {stats.avg_triage_hours != null
              ? `${stats.avg_triage_hours}h`
              : "—"}
          </p>
        </div>
      </div>

      {/* Severity breakdown */}
      <div className="mb-6">
        <h3 className="mb-3 text-sm font-semibold text-bark">
          Pending by Severity
        </h3>
        <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
          {(["critical", "high", "medium", "low"] as const).map((sev: Severity) => (
            <div
              key={sev}
              className={`rounded-card p-3 text-center ${SEVERITY_CARD_BG[sev]}`}
            >
              <span className="text-lg">{SEVERITY_ICONS[sev]}</span>
              <p className="mt-1 text-lg font-bold text-bark">
                {stats.severity_breakdown[sev] ?? 0}
              </p>
              <p className="text-xs capitalize text-bark-muted">{sev}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Trend chart (bar chart using divs) */}
      <div className="mb-4">
        <h3 className="mb-3 text-sm font-semibold text-bark">
          Daily Resolved (14d)
        </h3>
        <div className="flex items-end gap-1" style={{ height: "120px" }}>
          {stats.trend.map((point) => {
            const height =
              point.count > 0
                ? Math.max((point.count / maxTrend) * 100, 4)
                : 2;
            return (
              <div
                key={point.date}
                className="group relative flex-1"
                style={{ height: "100%" }}
              >
                <div
                  className="absolute bottom-0 w-full rounded-t bg-accent/60 transition-colors group-hover:bg-accent"
                  style={{ height: `${height}%` }}
                />
                <div className="absolute -top-5 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-nav-bg px-1.5 py-0.5 text-xs text-cream group-hover:block">
                  {point.date.slice(5)}: {point.count}
                </div>
              </div>
            );
          })}
        </div>
        <div className="mt-1 flex justify-between text-xs text-bark-light">
          <span>{stats.trend[0]?.date.slice(5)}</span>
          <span>{stats.trend[stats.trend.length - 1]?.date.slice(5)}</span>
        </div>
      </div>
    </div>
  );
}
