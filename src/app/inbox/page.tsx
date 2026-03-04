"use client";

import { useCallback, useEffect, useState } from "react";
import InboxSidebar from "@/components/InboxSidebar";
import NotificationCard from "@/components/NotificationCard";
import NotificationDetail from "@/components/NotificationDetail";
import TaskCreatorModal from "@/components/TaskCreatorModal";
import { useNotifications } from "@/hooks/useNotifications";
import { archiveNotification, markNotificationRead } from "@/lib/notificationApi";
import type { Source } from "@/lib/notificationTypes";

export default function InboxPage() {
  const {
    notifications,
    unreadCounts,
    connected,
    activeFilter,
    setActiveFilter,
    searchQuery,
    setSearchQuery,
    selectedNotification,
    setSelectedId,
    markRead,
    archive,
  } = useNotifications();

  const [showTaskCreator, setShowTaskCreator] = useState(false);

  const handleSelect = useCallback(
    (id: string) => {
      setSelectedId(id);
      const n = notifications.find((n) => n.id === id);
      if (n && n.triage_status === "unread") {
        markRead(id);
        markNotificationRead(id).catch(console.error);
      }
    },
    [notifications, setSelectedId, markRead],
  );

  const handleArchive = useCallback(
    (id: string) => {
      archive(id);
      archiveNotification(id).catch(console.error);
      if (selectedNotification?.id === id) setSelectedId(null);
    },
    [archive, selectedNotification, setSelectedId],
  );

  // Keyboard navigation
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      // Cmd+1-6 source filters
      if (e.metaKey || e.ctrlKey) {
        const sources: (Source | "all")[] = ["all", "gmail", "outlook", "slack", "asana", "plane"];
        const num = parseInt(e.key);
        if (num >= 1 && num <= sources.length) {
          e.preventDefault();
          setActiveFilter(sources[num - 1]);
          return;
        }
      }

      const currentIdx = selectedNotification ? notifications.findIndex((n) => n.id === selectedNotification.id) : -1;

      switch (e.key) {
        case "j":
        case "ArrowDown": {
          e.preventDefault();
          const next = Math.min(currentIdx + 1, notifications.length - 1);
          if (notifications[next]) handleSelect(notifications[next].id);
          break;
        }
        case "k":
        case "ArrowUp": {
          e.preventDefault();
          const prev = Math.max(currentIdx - 1, 0);
          if (notifications[prev]) handleSelect(notifications[prev].id);
          break;
        }
        case "a":
          if (selectedNotification) handleArchive(selectedNotification.id);
          break;
        case "t":
          if (selectedNotification) setShowTaskCreator(true);
          break;
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [notifications, selectedNotification, handleSelect, handleArchive, setActiveFilter]);

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4">
      {/* Sidebar */}
      <InboxSidebar
        activeFilter={activeFilter}
        onFilterChange={setActiveFilter}
        unreadCounts={unreadCounts}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      {/* Feed */}
      <div className="flex w-80 flex-col gap-1 overflow-y-auto">
        {!connected && (
          <div className="mb-2 rounded-lg bg-sev-critical/20 p-2 text-center text-xs text-bark-muted">
            Connecting to backend...
          </div>
        )}
        {notifications.length === 0 ? (
          <div className="flex flex-1 items-center justify-center text-sm text-bark-muted">
            {connected ? "No notifications" : "Waiting for connection..."}
          </div>
        ) : (
          notifications.map((n) => (
            <NotificationCard
              key={n.id}
              notification={n}
              isSelected={selectedNotification?.id === n.id}
              onSelect={handleSelect}
              onArchive={handleArchive}
            />
          ))
        )}
      </div>

      {/* Detail */}
      <NotificationDetail
        notification={selectedNotification}
        onClose={() => setSelectedId(null)}
        onArchive={handleArchive}
        onCreateTask={() => setShowTaskCreator(true)}
      />

      <TaskCreatorModal
        isOpen={showTaskCreator}
        onClose={() => setShowTaskCreator(false)}
        notification={selectedNotification}
      />
    </div>
  );
}
