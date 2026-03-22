"use client";

import { useCallback, useEffect, useState } from "react";
import type { PendingAction } from "@/lib/api";

interface ConfirmationCardProps {
  action: PendingAction;
  onConfirm: () => void;
  onReject: () => void;
}

const TIMEOUT_SECONDS = 30;

export default function ConfirmationCard({
  action,
  onConfirm,
  onReject,
}: ConfirmationCardProps) {
  const [remaining, setRemaining] = useState(TIMEOUT_SECONDS);

  // Countdown — auto-reject when it hits 0
  useEffect(() => {
    if (remaining <= 0) {
      onReject();
      return;
    }
    const timer = setTimeout(() => setRemaining((r) => r - 1), 1000);
    return () => clearTimeout(timer);
  }, [remaining, onReject]);

  // Keyboard shortcuts: Enter = confirm, Escape = reject
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        onConfirm();
      } else if (e.key === "Escape") {
        e.preventDefault();
        onReject();
      }
    },
    [onConfirm, onReject],
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const isCreate = action.action_type === "create_task";

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-bark/40 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md rounded-card bg-card-bg p-6 shadow-card">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-bark">
            {isCreate ? "Create Task" : "Complete Task"}
          </h3>
          <span className="rounded-pill bg-cream-dark px-2.5 py-1 text-xs font-medium text-bark-muted tabular-nums">
            {remaining}s
          </span>
        </div>

        {/* Countdown bar */}
        <div className="mb-4 h-1 overflow-hidden rounded-full bg-cream-dark">
          <div
            className="h-full rounded-full bg-accent transition-all duration-1000 ease-linear"
            style={{ width: `${(remaining / TIMEOUT_SECONDS) * 100}%` }}
          />
        </div>

        {/* Action details */}
        <div className="mb-6 space-y-2 rounded-lg bg-cream-light p-4 text-sm">
          <div className="flex justify-between">
            <span className="text-bark-muted">Project</span>
            <span className="font-medium text-bark">{action.project_name}</span>
          </div>
          {isCreate && action.title && (
            <div className="flex justify-between">
              <span className="text-bark-muted">Title</span>
              <span className="font-medium text-bark">{action.title}</span>
            </div>
          )}
          {isCreate && action.priority && action.priority !== "none" && (
            <div className="flex justify-between">
              <span className="text-bark-muted">Priority</span>
              <span className="font-medium capitalize text-bark">
                {action.priority}
              </span>
            </div>
          )}
          {!isCreate && action.task_ref && (
            <div className="flex justify-between">
              <span className="text-bark-muted">Task</span>
              <span className="font-medium text-bark">{action.task_ref}</span>
            </div>
          )}
        </div>

        {/* Buttons */}
        <div className="flex gap-3">
          <button
            onClick={onReject}
            className="flex-1 rounded-pill border border-cream-dark px-4 py-2.5 text-sm font-medium text-bark-muted transition hover:bg-cream-dark"
          >
            Reject <kbd className="ml-1 text-xs opacity-60">Esc</kbd>
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 rounded-pill bg-accent px-4 py-2.5 text-sm font-medium text-cream transition hover:opacity-90"
          >
            Confirm <kbd className="ml-1 text-xs opacity-80">Enter</kbd>
          </button>
        </div>
      </div>
    </div>
  );
}
