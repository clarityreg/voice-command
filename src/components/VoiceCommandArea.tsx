"use client";

import Link from "next/link";
import { useVoice } from "@/hooks/useVoice";
import type { VoiceState } from "@/hooks/useVoice";

function WaveformBars({ level }: { level: number }) {
  // 5 bars with different multipliers for visual variety
  const multipliers = [0.4, 0.7, 1.0, 0.7, 0.4];
  return (
    <div className="flex items-center justify-center gap-1">
      {multipliers.map((m, i) => (
        <div
          key={i}
          className="w-1.5 rounded-full bg-sev-critical transition-all duration-75"
          style={{ height: `${Math.max(4, level * 32 * m)}px` }}
        />
      ))}
    </div>
  );
}

function BouncingDots() {
  return (
    <div className="flex items-center justify-center gap-1.5">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="h-2 w-2 rounded-full bg-accent animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}

// Large mic icon for the command area
function MicLargeIcon() {
  return (
    <svg className="h-8 w-8" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5z" />
      <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
    </svg>
  );
}

function MicOnLargeIcon() {
  return (
    <svg className="h-8 w-8" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
      <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
    </svg>
  );
}

function SpinnerLargeIcon() {
  return (
    <svg className="h-8 w-8 animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

const stateConfig: Record<VoiceState, { bg: string; label: string; pulse: boolean }> = {
  idle: { bg: "bg-nav-bg", label: "Speak", pulse: false },
  listening: { bg: "bg-sev-critical", label: "Listening...", pulse: true },
  processing: { bg: "bg-sev-high", label: "Thinking...", pulse: true },
  speaking: { bg: "bg-accent", label: "Speaking...", pulse: false },
};

export default function VoiceCommandArea({ pending }: { pending: number }) {
  const { state, audioLevel, lastResponse, toggle, dismissResponse } = useVoice();
  const config = stateConfig[state];

  return (
    <div className="rounded-card bg-card-bg p-6 shadow-card">
      <div className="flex flex-col items-center gap-4">
        {/* Large mic button */}
        <button
          onClick={toggle}
          disabled={state === "processing"}
          aria-label={config.label}
          className={`flex h-20 w-20 items-center justify-center rounded-full ${config.bg} text-cream shadow-lg transition hover:opacity-90 disabled:opacity-50 ${
            config.pulse ? "animate-pulse" : ""
          }`}
        >
          {state === "listening" ? (
            <MicOnLargeIcon />
          ) : state === "processing" ? (
            <SpinnerLargeIcon />
          ) : (
            <MicLargeIcon />
          )}
        </button>

        {/* State indicator */}
        <div className="flex flex-col items-center gap-2">
          {state === "idle" && (
            <p className="text-sm text-bark-muted">
              Tap to speak or <kbd className="rounded bg-cream-dark px-1.5 py-0.5 text-xs font-mono">⌘⇧Space</kbd>
            </p>
          )}
          {state === "listening" && (
            <div className="flex flex-col items-center gap-2">
              <p className="text-sm font-medium text-bark">Listening...</p>
              <WaveformBars level={audioLevel} />
            </div>
          )}
          {state === "processing" && (
            <p className="text-sm font-medium text-bark">Thinking...</p>
          )}
          {state === "speaking" && (
            <div className="flex flex-col items-center gap-2">
              <p className="text-sm font-medium text-bark">Speaking...</p>
              <BouncingDots />
            </div>
          )}
        </div>

        {/* Last response */}
        {lastResponse && (
          <button
            onClick={dismissResponse}
            className="w-full rounded-lg bg-cream-dark/50 p-3 text-left text-sm text-bark transition hover:bg-cream-dark"
          >
            {lastResponse}
          </button>
        )}

        {/* Pending items + triage link */}
        <div className="flex w-full items-center justify-between border-t border-cream-dark pt-4">
          <p className="text-sm text-bark-muted">
            {pending === 0
              ? "All clear! No pending items."
              : `${pending} pending item${pending !== 1 ? "s" : ""}`}
          </p>
          <Link
            href={pending > 0 ? "/triage" : "/dashboard"}
            className="rounded-pill bg-nav-bg px-4 py-2 text-sm font-medium text-cream transition hover:opacity-90"
          >
            {pending > 0 ? "Start Triage" : "View Dashboard"}
          </Link>
        </div>
      </div>
    </div>
  );
}
