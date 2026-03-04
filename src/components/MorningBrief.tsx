"use client";

import { useEffect, useState } from "react";
import { getMorningBrief, type MorningBrief } from "@/lib/api";

const BRIEF_DATE_KEY = "clarity-last-brief-date";

function shouldShowBrief(): boolean {
  if (typeof window === "undefined") return false;
  const lastDate = localStorage.getItem(BRIEF_DATE_KEY);
  const today = new Date().toDateString();
  return lastDate !== today;
}

function markBriefSeen(): void {
  localStorage.setItem(BRIEF_DATE_KEY, new Date().toDateString());
}

export default function MorningBriefCard() {
  const [brief, setBrief] = useState<MorningBrief | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!shouldShowBrief()) return;
    getMorningBrief()
      .then((data) => {
        setBrief(data);
        setVisible(true);
      })
      .catch(() => {});
  }, []);

  const dismiss = () => {
    markBriefSeen();
    setVisible(false);
  };

  if (!visible || !brief) return null;

  return (
    <div className="rounded-card bg-source-posthog/20 p-5 shadow-card">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">{"\u2600\uFE0F"}</span>
          <h3 className="font-semibold text-bark">Morning Brief</h3>
        </div>
        <button
          onClick={dismiss}
          className="text-xs text-bark-muted hover:text-bark"
        >
          Dismiss
        </button>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="rounded-md bg-card-bg/60 px-3 py-2">
          <span className="font-bold text-bark">{brief.new_errors_24h}</span>
          <span className="ml-1 text-bark-muted">new errors</span>
        </div>
        <div className="rounded-md bg-card-bg/60 px-3 py-2">
          <span className="font-bold text-bark">{brief.new_vulns_24h}</span>
          <span className="ml-1 text-bark-muted">new vulns</span>
        </div>
        <div className="rounded-md bg-card-bg/60 px-3 py-2">
          <span className="font-bold text-bark">{brief.actioned_yesterday}</span>
          <span className="ml-1 text-bark-muted">actioned</span>
        </div>
        <div className="rounded-md bg-card-bg/60 px-3 py-2">
          <span className="font-bold text-bark">{brief.pending_total}</span>
          <span className="ml-1 text-bark-muted">pending</span>
        </div>
      </div>
      {brief.top_severity && (
        <p className="mt-3 text-xs text-bark-muted">
          Top severity: <span className="font-medium text-bark">{brief.top_severity}</span>
        </p>
      )}
    </div>
  );
}
