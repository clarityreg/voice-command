"use client";

import type { Notification } from "@/lib/notificationTypes";
import { SOURCE_CONFIG, PRIORITY_CONFIG } from "@/lib/notificationTypes";

function formatTimeAgo(timestamp: string): string {
  const now = Date.now();
  const date = new Date(timestamp).getTime();
  const diffMins = Math.floor((now - date) / 60000);
  if (diffMins < 1) return "now";
  if (diffMins < 60) return `${diffMins}m`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d`;
  return new Date(timestamp).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

interface NotificationCardProps {
  notification: Notification;
  isSelected: boolean;
  onSelect: (id: string) => void;
  onArchive: (id: string) => void;
  onActioned?: (id: string) => void;
}

export default function NotificationCard({ notification, isSelected, onSelect, onArchive, onActioned }: NotificationCardProps) {
  const config = SOURCE_CONFIG[notification.source];
  const isUnread = notification.triage_status === "unread";
  const isActioned = notification.triage_status === "actioned";
  const isEmail = notification.source === "gmail" || notification.source === "outlook";

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(notification.id)}
      onKeyDown={(e) => e.key === "Enter" && onSelect(notification.id)}
      className={`group relative flex cursor-pointer transition-all ${
        isSelected
          ? "rounded-card bg-accent/10 shadow-card ring-2 ring-accent"
          : "rounded-lg bg-card-bg hover:shadow-card"
      }`}
    >
      {/* Source indicator */}
      <div className="w-1.5 min-h-full flex-shrink-0 rounded-l-lg" style={{ background: config.color }} />

      <div className="flex-1 p-3 min-w-0 overflow-hidden">
        {/* Header */}
        <div className="mb-1 flex items-center justify-between">
          <span className="text-xs font-semibold" style={{ color: config.color }}>
            {config.icon} {notification.source_account}
          </span>
          <span className="text-xs font-medium text-bark-muted">{formatTimeAgo(notification.timestamp)}</span>
        </div>

        {/* Title */}
        <div className={`flex items-center gap-1.5 text-sm leading-snug ${isActioned ? "font-medium text-bark-light" : isUnread ? "font-bold text-bark" : "font-medium text-bark-muted"}`}>
          {isActioned && <span className="h-3 w-3 flex-shrink-0 text-green-600">✓</span>}
          {!isActioned && (notification.priority === "urgent" || notification.priority === "high") && (
            <span className="h-2 w-2 flex-shrink-0 rounded-full" style={{ background: PRIORITY_CONFIG[notification.priority].color }} />
          )}
          <span className="truncate">{notification.title}</span>
        </div>

        {/* Body preview */}
        <div className="mt-0.5 truncate text-xs text-bark-light">
          <span className="font-semibold text-bark-muted">{notification.sender_name}</span>
          {notification.body && (
            <>
              <span className="mx-1 opacity-50">&mdash;</span>
              <span>{notification.body.slice(0, 120)}</span>
            </>
          )}
        </div>

        {/* Tags */}
        {(notification.channel_name || notification.project_name) && (
          <div className="mt-1.5 flex gap-1.5">
            {notification.channel_name && (
              <span className="rounded-pill bg-cream-dark px-2 py-0.5 text-[10px] font-semibold text-bark-muted">
                #{notification.channel_name}
              </span>
            )}
            {notification.project_name && (
              <span className="rounded-pill bg-cream-dark px-2 py-0.5 text-[10px] font-semibold text-bark-muted">
                {notification.project_name}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Quick actions */}
      <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1 opacity-0 transition group-hover:opacity-100">
        {isEmail && !isActioned && onActioned && (
          <button
            onClick={(e) => { e.stopPropagation(); onActioned(notification.id); }}
            className="rounded-lg bg-green-600/20 px-2 py-1 text-xs font-medium text-green-700"
          >
            Actioned
          </button>
        )}
        <button
          onClick={(e) => { e.stopPropagation(); onArchive(notification.id); }}
          className="rounded-lg bg-accent/20 px-2 py-1 text-xs font-medium text-accent"
        >
          Archive
        </button>
      </div>
    </div>
  );
}
