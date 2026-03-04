"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const DEFAULT_FOCUS_MINUTES = 25;
const DEFAULT_BREAK_MINUTES = 5;

type TimerPhase = "idle" | "focus" | "break" | "done";

export default function FocusTimer() {
  const [phase, setPhase] = useState<TimerPhase>("idle");
  const [secondsLeft, setSecondsLeft] = useState(DEFAULT_FOCUS_MINUTES * 60);
  const [totalSeconds, setTotalSeconds] = useState(DEFAULT_FOCUS_MINUTES * 60);
  const [running, setRunning] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearTimer = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startFocus = useCallback(() => {
    clearTimer();
    const total = DEFAULT_FOCUS_MINUTES * 60;
    setTotalSeconds(total);
    setSecondsLeft(total);
    setPhase("focus");
    setRunning(true);
  }, [clearTimer]);

  const startBreak = useCallback(() => {
    clearTimer();
    const total = DEFAULT_BREAK_MINUTES * 60;
    setTotalSeconds(total);
    setSecondsLeft(total);
    setPhase("break");
    setRunning(true);
  }, [clearTimer]);

  const pause = useCallback(() => {
    clearTimer();
    setRunning(false);
  }, [clearTimer]);

  const resume = useCallback(() => {
    setRunning(true);
  }, []);

  const reset = useCallback(() => {
    clearTimer();
    setPhase("idle");
    setRunning(false);
    setSecondsLeft(DEFAULT_FOCUS_MINUTES * 60);
    setTotalSeconds(DEFAULT_FOCUS_MINUTES * 60);
  }, [clearTimer]);

  useEffect(() => {
    if (!running) return;
    if (phase !== "focus" && phase !== "break") return;

    intervalRef.current = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          clearTimer();
          setPhase("done");
          setRunning(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return clearTimer;
  }, [phase, running, clearTimer]);

  // Format time
  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  const display = `${minutes}:${seconds.toString().padStart(2, "0")}`;

  // Ring progress
  const circumference = 2 * Math.PI * 54;
  const ratio = totalSeconds > 0 ? secondsLeft / totalSeconds : 0;
  const filled = circumference * ratio;
  const ringColor =
    phase === "break"
      ? "#A8D5A2"
      : phase === "done"
        ? "#A8D5A2"
        : secondsLeft > totalSeconds * 0.25
          ? "#E8D77A"
          : "#F4A4B8";

  const isRunning = running;

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Timer ring */}
      <div className="relative mx-auto h-32 w-32">
        <svg viewBox="0 0 120 120" className="h-full w-full -rotate-90">
          <circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke="#EDE7DB"
            strokeWidth="8"
          />
          <circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke={ringColor}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${filled} ${circumference - filled}`}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-bark" data-testid="timer-display">
            {display}
          </span>
          <span className="text-xs text-bark-muted">
            {phase === "idle"
              ? "ready"
              : phase === "focus"
                ? "focus"
                : phase === "break"
                  ? "break"
                  : "done!"}
          </span>
        </div>
      </div>

      {/* Done notification */}
      {phase === "done" && (
        <div className="rounded-card bg-sev-low/20 px-4 py-3 text-center shadow-card">
          <p className="text-sm font-medium text-bark">
            Time&apos;s up! Take a break.
          </p>
        </div>
      )}

      {/* Controls */}
      <div className="flex gap-2">
        {phase === "idle" && (
          <button
            onClick={startFocus}
            className="rounded-pill bg-nav-bg px-4 py-2 text-sm font-medium text-cream transition hover:opacity-90"
          >
            Start Focus
          </button>
        )}
        {phase === "done" && (
          <>
            <button
              onClick={startBreak}
              className="rounded-pill bg-sev-low/30 px-4 py-2 text-sm font-medium text-bark transition hover:opacity-90"
            >
              Start Break
            </button>
            <button
              onClick={startFocus}
              className="rounded-pill bg-nav-bg px-4 py-2 text-sm font-medium text-cream transition hover:opacity-90"
            >
              New Focus
            </button>
          </>
        )}
        {(phase === "focus" || phase === "break") && (
          <>
            {isRunning ? (
              <button
                onClick={pause}
                className="rounded-pill bg-cream-dark px-4 py-2 text-sm font-medium text-bark transition hover:bg-cream"
              >
                Pause
              </button>
            ) : (
              <button
                onClick={resume}
                className="rounded-pill bg-nav-bg px-4 py-2 text-sm font-medium text-cream transition hover:opacity-90"
              >
                Resume
              </button>
            )}
            <button
              onClick={reset}
              className="rounded-pill bg-cream-dark px-4 py-2 text-sm font-medium text-bark transition hover:bg-cream"
            >
              Reset
            </button>
          </>
        )}
      </div>
    </div>
  );
}
