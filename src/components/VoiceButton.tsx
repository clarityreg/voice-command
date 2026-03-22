"use client";

import { useVoice } from "@/hooks/useVoice";
import type { VoiceState } from "@/hooks/useVoice";
import ConfirmationCard from "@/components/ConfirmationCard";

const stateConfig: Record<VoiceState, { bg: string; label: string; pulse: boolean }> = {
  idle: { bg: "bg-nav-bg", label: "Speak", pulse: false },
  listening: { bg: "bg-sev-critical", label: "Listening...", pulse: true },
  processing: { bg: "bg-sev-high", label: "Thinking...", pulse: true },
  speaking: { bg: "bg-accent", label: "Speaking...", pulse: false },
};

export default function VoiceButton() {
  const { state, lastResponse, pendingAction, toggle, dismissResponse, confirmAction, rejectAction } = useVoice();
  const config = stateConfig[state];

  return (
    <>
      <div className="fixed bottom-20 right-4 z-50 flex flex-col items-end gap-2 md:hidden">
        {lastResponse && (
          <button
            onClick={dismissResponse}
            className="max-w-xs rounded-card bg-card-bg p-3 text-left text-sm text-bark shadow-card"
          >
            {lastResponse}
          </button>
        )}
        <button
          onClick={toggle}
          disabled={state === "processing"}
          aria-label={config.label}
          className={`flex h-12 w-12 items-center justify-center rounded-full ${config.bg} text-cream shadow-lg transition hover:opacity-90 disabled:opacity-50 ${
            config.pulse ? "animate-pulse" : ""
          }`}
        >
          {state === "listening" ? (
            <MicOnIcon />
          ) : state === "processing" ? (
            <SpinnerIcon />
          ) : (
            <MicIcon />
          )}
        </button>
      </div>
      {pendingAction && (
        <ConfirmationCard
          action={pendingAction}
          onConfirm={confirmAction}
          onReject={rejectAction}
        />
      )}
    </>
  );
}

export function MicIcon({ className = "h-5 w-5" }: { className?: string } = {}) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5z" />
      <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
    </svg>
  );
}

function MicOnIcon() {
  return (
    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
      <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
      <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}
