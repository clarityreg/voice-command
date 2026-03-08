"use client";

import { useCallback, useEffect, useState } from "react";
import InboxSidebar from "@/components/InboxSidebar";
import NotificationCard from "@/components/NotificationCard";
import NotificationDetail from "@/components/NotificationDetail";
import TaskCreatorModal from "@/components/TaskCreatorModal";
import { useNotifications } from "@/hooks/useNotifications";
import { actionNotification, archiveNotification, markNotificationRead } from "@/lib/notificationApi";
import { SOURCE_CONFIG, SOURCES } from "@/lib/notificationTypes";

const ALL_CONFIG = { label: "All", icon: "📥" } as const;

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
    actioned,
    loadMore,
    hasMore,
    loadingMore,
  } = useNotifications();

  const [showTaskCreator, setShowTaskCreator] = useState(false);
  const [showMobileDetail, setShowMobileDetail] = useState(false);

  const handleSelect = useCallback(
    (id: string) => {
      setSelectedId(id);
      setShowMobileDetail(true);
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
      if (selectedNotification?.id === id) {
        setSelectedId(null);
        setShowMobileDetail(false);
      }
    },
    [archive, selectedNotification, setSelectedId],
  );

  const handleActioned = useCallback(
    (id: string) => {
      actioned(id);
      actionNotification(id).catch(console.error);
    },
    [actioned],
  );

  const handleMobileBack = useCallback(() => {
    setShowMobileDetail(false);
    setSelectedId(null);
  }, [setSelectedId]);

  const handleDetailClose = useCallback(() => {
    setSelectedId(null);
    setShowMobileDetail(false);
  }, [setSelectedId]);

  const handleOpenTaskCreator = useCallback(() => {
    setShowTaskCreator(true);
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      // Cmd+1-6 source filters
      if (e.metaKey || e.ctrlKey) {
        const num = parseInt(e.key);
        if (num >= 1 && num <= SOURCES.length) {
          e.preventDefault();
          setActiveFilter(SOURCES[num - 1]);
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
        case "d":
          if (selectedNotification) handleActioned(selectedNotification.id);
          break;
        case "t":
          if (selectedNotification) setShowTaskCreator(true);
          break;
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [notifications, selectedNotification, handleSelect, handleArchive, handleActioned, setActiveFilter]);

  return (
    <div className="flex h-[calc(100vh-8rem)] md:h-[calc(100vh-4rem)] gap-4">
      {/* Desktop sidebar — lg only */}
      <InboxSidebar
        activeFilter={activeFilter}
        onFilterChange={setActiveFilter}
        unreadCounts={unreadCounts}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      {/* Mobile/Tablet source filter pills */}
      <div className="flex flex-col flex-1 lg:contents gap-3">
        <div className="flex gap-2 overflow-x-auto pb-2 lg:hidden shrink-0">
          {SOURCES.map((source) => {
            const isAll = source === "all";
            const config = isAll ? ALL_CONFIG : SOURCE_CONFIG[source];
            const isActive = activeFilter === source;
            return (
              <button
                key={source}
                onClick={() => setActiveFilter(source)}
                className={`flex shrink-0 items-center gap-1.5 rounded-pill px-3 py-1.5 text-xs font-medium transition ${
                  isActive ? "bg-accent text-white" : "bg-card-bg text-bark hover:bg-cream-dark"
                }`}
              >
                <span>{config.icon}</span>
                {config.label}
              </button>
            );
          })}
        </div>

        {/* Feed */}
        <div className={`flex w-full md:w-80 flex-col gap-1 overflow-y-auto shrink-0 ${showMobileDetail ? "hidden md:flex" : "flex"}`}>
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
            <>
              {notifications.map((n) => (
                <NotificationCard
                  key={n.id}
                  notification={n}
                  isSelected={selectedNotification?.id === n.id}
                  onSelect={handleSelect}
                  onArchive={handleArchive}
                  onActioned={handleActioned}
                />
              ))}
              {hasMore && (
                <button
                  onClick={loadMore}
                  disabled={loadingMore}
                  className="mt-2 rounded-lg bg-cream px-3 py-2 text-xs font-medium text-bark-muted hover:bg-cream-dark disabled:opacity-50"
                >
                  {loadingMore ? "Loading..." : "Load More"}
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Detail — full-screen overlay on mobile, right panel on md+ */}
      <div className={`${showMobileDetail && selectedNotification ? "fixed inset-0 z-40 bg-cream md:relative md:inset-auto md:z-auto md:bg-transparent" : "hidden md:flex"} md:flex md:flex-1`}>
        {showMobileDetail && selectedNotification && (
          <button
            onClick={handleMobileBack}
            className="flex items-center gap-1 px-4 py-3 text-sm font-medium text-accent md:hidden"
          >
            ← Back
          </button>
        )}
        <NotificationDetail
          notification={selectedNotification}
          onClose={handleDetailClose}
          onArchive={handleArchive}
          onActioned={handleActioned}
          onCreateTask={handleOpenTaskCreator}
        />
      </div>

      <TaskCreatorModal
        isOpen={showTaskCreator}
        onClose={() => setShowTaskCreator(false)}
        notification={selectedNotification}
      />
    </div>
  );
}
