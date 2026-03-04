"use client";

import { useEffect, useState } from "react";
import StatusBar from "@/components/StatusBar";
import FocusTimer from "@/components/FocusTimer";
import MorningBriefCard from "@/components/MorningBrief";
import VoiceCommandArea from "@/components/VoiceCommandArea";
import { getStatus, type TriageStatus } from "@/lib/api";

function ScoreRing({ pending }: { pending: number }) {
  const max = 20;
  const ratio = Math.min(pending / max, 1);
  const circumference = 2 * Math.PI * 54;
  const filled = circumference * ratio;

  return (
    <div className="relative mx-auto h-40 w-40">
      <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
        <circle
          cx="60"
          cy="60"
          r="54"
          fill="none"
          stroke="#EDE7DB"
          strokeWidth="10"
        />
        <circle
          cx="60"
          cy="60"
          r="54"
          fill="none"
          stroke={pending === 0 ? "#A8D5A2" : pending <= 5 ? "#E8D77A" : "#F4A4B8"}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference - filled}`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-4xl font-bold text-bark">{pending}</span>
        <span className="text-xs text-bark-muted">pending</span>
      </div>
    </div>
  );
}

export default function FocusPage() {
  const [status, setStatus] = useState<TriageStatus | null>(null);

  useEffect(() => {
    getStatus().then(setStatus).catch(() => {});
  }, []);

  const pending = status?.pending_count ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <ScoreRing pending={pending} />

      <div className="flex justify-center gap-4 text-2xl">
        <span title="Bugs">{"\uD83D\uDC1B"}</span>
        <span title="Security">{"\uD83D\uDEE1\uFE0F"}</span>
        <span title="Tasks">{"\uD83D\uDCCB"}</span>
        <span title="Done">{"\u2705"}</span>
      </div>

      <MorningBriefCard />

      <FocusTimer />

      <StatusBar />

      <VoiceCommandArea pending={pending} />
    </div>
  );
}
