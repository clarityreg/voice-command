"use client";

import { useEffect, useRef, useState } from "react";
import type { Source } from "@/lib/notificationTypes";
import { SOURCE_CONFIG, SOURCES } from "@/lib/notificationTypes";
import { syncEmails } from "@/lib/notificationApi";

const ALL_CONFIG = { label: "All", color: "#6366f1", icon: "📥" } as const;

interface InboxSidebarProps {
  activeFilter: Source | "all";
  onFilterChange: (filter: Source | "all") => void;
  unreadCounts: Record<string, number>;
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

export default function InboxSidebar({ activeFilter, onFilterChange, unreadCounts, searchQuery, onSearchChange }: InboxSidebarProps) {
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    try {
      const { synced } = await syncEmails();
      setSyncResult(`${synced} synced`);
      timeoutRef.current = setTimeout(() => setSyncResult(null), 3000);
    } catch {
      setSyncResult("Sync failed");
      timeoutRef.current = setTimeout(() => setSyncResult(null), 3000);
    }
    setSyncing(false);
  };

  return (
    <div className="hidden lg:flex w-52 flex-col rounded-card bg-card-bg p-4 shadow-card shrink-0">
      {/* Search */}
      <input
        type="text"
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search..."
        className="mb-2 rounded-lg border border-cream-dark bg-cream-light px-3 py-2 text-sm text-bark outline-none focus:border-accent"
      />

      {/* Sync */}
      <button
        onClick={handleSync}
        disabled={syncing}
        className="mb-4 flex items-center justify-center gap-1.5 rounded-lg bg-cream px-3 py-1.5 text-xs font-medium text-bark hover:bg-cream-dark disabled:opacity-50"
      >
        {syncing ? "Syncing..." : syncResult || "↻ Sync Emails"}
      </button>

      {/* Filters */}
      <div className="flex flex-col gap-1">
        {SOURCES.map((source, i) => {
          const isAll = source === "all";
          const config = isAll ? ALL_CONFIG : SOURCE_CONFIG[source];
          const count = isAll ? (unreadCounts.total || 0) : (unreadCounts[source] || 0);
          const isActive = activeFilter === source;

          return (
            <button
              key={source}
              onClick={() => onFilterChange(source)}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${
                isActive ? "bg-accent/10 font-semibold text-accent" : "text-bark hover:bg-cream-dark"
              }`}
            >
              <span className="w-5 text-center text-sm">{config.icon}</span>
              <span className="flex-1 text-left">{config.label}</span>
              {count > 0 && (
                <span className="rounded-pill px-1.5 py-0.5 text-[10px] font-bold text-white" style={{ background: config.color }}>
                  {count}
                </span>
              )}
              <span className="text-[10px] text-bark-light">&#8984;{i + 1}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
