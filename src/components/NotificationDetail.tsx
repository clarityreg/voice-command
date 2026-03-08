"use client";

import { useCallback, useEffect, useState } from "react";
import type { Notification } from "@/lib/notificationTypes";
import { SOURCE_CONFIG, PRIORITY_CONFIG } from "@/lib/notificationTypes";
import { replyToNotification, snoozeNotification } from "@/lib/notificationApi";

interface NotificationDetailProps {
  notification: Notification | null;
  onClose: () => void;
  onArchive: (id: string) => void;
  onActioned: (id: string) => void;
  onCreateTask: () => void;
}

const SNOOZE_OPTIONS = [
  { minutes: 30, label: "30 min" },
  { minutes: 60, label: "1 hour" },
  { minutes: 240, label: "4 hours" },
  { minutes: 1440, label: "Tomorrow" },
];

export default function NotificationDetail({ notification, onClose, onArchive, onActioned, onCreateTask }: NotificationDetailProps) {
  const [replyText, setReplyText] = useState("");
  const [isReplying, setIsReplying] = useState(false);
  const [showSnoozeMenu, setShowSnoozeMenu] = useState(false);

  useEffect(() => {
    setReplyText("");
    setShowSnoozeMenu(false);
  }, [notification?.id]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const handleReply = useCallback(async () => {
    if (!notification || !replyText.trim()) return;
    setIsReplying(true);
    try {
      await replyToNotification(notification.id, replyText, notification.source, notification.source_account, notification.source_id);
      setReplyText("");
    } catch (e) {
      console.error("Reply failed:", e);
    }
    setIsReplying(false);
  }, [notification, replyText]);

  const handleArchive = useCallback(() => {
    if (!notification) return;
    onArchive(notification.id);
    onClose();
  }, [notification, onArchive, onClose]);

  const handleActioned = useCallback(() => {
    if (!notification) return;
    onActioned(notification.id);
    onClose();
  }, [notification, onActioned, onClose]);

  const handleSnooze = useCallback(async (minutes: number) => {
    if (!notification) return;
    await snoozeNotification(notification.id, minutes).catch(console.error);
    setShowSnoozeMenu(false);
    onClose();
  }, [notification, onClose]);

  if (!notification) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center rounded-card bg-card-bg">
        <p className="text-lg font-semibold text-bark-muted">Select a notification</p>
        <p className="mt-1 text-sm text-bark-light">Use arrow keys to navigate</p>
      </div>
    );
  }

  const config = SOURCE_CONFIG[notification.source];
  const isEmail = notification.source === "gmail" || notification.source === "outlook";
  const isActioned = notification.triage_status === "actioned";

  return (
    <div className="flex flex-1 flex-col overflow-hidden rounded-card bg-card-bg shadow-card">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-cream-dark p-4">
        <div className="flex items-center gap-2">
          <span className="rounded-pill px-3 py-1 text-xs font-bold text-white" style={{ background: config.color }}>
            {config.icon} {config.label}
          </span>
          <span className="text-xs font-medium text-bark-light">{notification.source_account}</span>
          {isActioned && (
            <span className="rounded-pill bg-green-100 px-2 py-0.5 text-xs font-bold text-green-700">
              ✓ Actioned
            </span>
          )}
        </div>
        <button onClick={onClose} className="rounded-lg px-2 py-1 text-sm font-medium text-bark-muted hover:bg-cream-dark">
          Close
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5">
        <h2 className="mb-2 text-xl font-bold text-bark">{notification.title}</h2>
        <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
          <span className="font-semibold text-bark">{notification.sender_name}</span>
          <span className="text-bark-light">
            {new Date(notification.timestamp).toLocaleString("en-GB", {
              weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
            })}
          </span>
          {notification.priority !== "normal" && (
            <span className="rounded-pill px-2 py-0.5 text-xs font-bold text-white" style={{ background: PRIORITY_CONFIG[notification.priority].color }}>
              {PRIORITY_CONFIG[notification.priority].label}
            </span>
          )}
        </div>
        {notification.channel_name && <p className="mb-1 text-sm text-bark-light">#{notification.channel_name}</p>}
        {notification.project_name && <p className="mb-1 text-sm text-bark-light">{notification.project_name}</p>}
        <div className="mt-4 whitespace-pre-wrap text-sm leading-relaxed text-bark">
          {notification.body || "No content"}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 border-t border-cream-dark p-4">
        {isEmail && !isActioned && (
          <button onClick={handleActioned} className="rounded-pill bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700">
            Actioned
          </button>
        )}
        <button onClick={handleArchive} className="rounded-pill bg-nav-bg px-4 py-2 text-sm font-medium text-cream hover:opacity-90">
          Archive
        </button>
        <div className="relative">
          <button onClick={() => setShowSnoozeMenu(!showSnoozeMenu)} className="rounded-pill bg-cream px-4 py-2 text-sm font-medium text-bark hover:bg-cream-dark">
            Snooze
          </button>
          {showSnoozeMenu && (
            <div className="absolute bottom-full left-0 mb-1 rounded-card bg-card-bg p-1 shadow-lg">
              {SNOOZE_OPTIONS.map((opt) => (
                <button key={opt.minutes} onClick={() => handleSnooze(opt.minutes)} className="block w-full rounded-lg px-4 py-2 text-left text-sm font-medium text-bark hover:bg-cream-dark">
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <button onClick={onCreateTask} className="rounded-pill bg-cream px-4 py-2 text-sm font-medium text-bark hover:bg-cream-dark">
          Create Task
        </button>
      </div>

      {/* Reply */}
      {isEmail && (
        <div className="border-t border-cream-dark p-4">
          <textarea
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Write a reply..."
            rows={3}
            className="w-full rounded-lg border border-cream-dark bg-cream-light p-3 text-sm text-bark outline-none focus:border-accent"
            onKeyDown={(e) => { if (e.metaKey && e.key === "Enter") handleReply(); }}
          />
          <div className="mt-2 flex items-center justify-between">
            <span className="text-xs text-bark-light">Cmd+Enter to send</span>
            <button
              disabled={!replyText.trim() || isReplying}
              onClick={handleReply}
              className="rounded-pill bg-nav-bg px-4 py-2 text-sm font-medium text-cream disabled:opacity-50"
            >
              {isReplying ? "Sending..." : "Send Reply"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
