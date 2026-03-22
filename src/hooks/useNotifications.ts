"use client";

import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import type { Notification, Source, ServiceStatus } from "@/lib/notificationTypes";
import { createWsClient } from "@/lib/wsClient";
import { getNotifications } from "@/lib/notificationApi";

type State = {
  notifications: Notification[];
  serviceStatuses: ServiceStatus[];
  connected: boolean;
};

type Action =
  | { type: "LOAD"; notifications: Notification[] }
  | { type: "ADD_OR_UPDATE"; notification: Notification }
  | { type: "UPDATE_ONE"; id: string; updates: Partial<Notification> }
  | { type: "REMOVE"; id: string }
  | { type: "SET_CONNECTED"; connected: boolean }
  | { type: "SET_SERVICE_STATUS"; status: ServiceStatus }
  | { type: "APPEND_OLDER"; notifications: Notification[] };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "LOAD":
      return { ...state, notifications: action.notifications };
    case "ADD_OR_UPDATE": {
      const idx = state.notifications.findIndex(
        (n) => n.id === action.notification.id || (n.source === action.notification.source && n.source_id === action.notification.source_id),
      );
      if (idx >= 0) {
        const updated = [...state.notifications];
        updated[idx] = { ...updated[idx], ...action.notification };
        return { ...state, notifications: updated };
      }
      return { ...state, notifications: [action.notification, ...state.notifications] };
    }
    case "UPDATE_ONE": {
      return {
        ...state,
        notifications: state.notifications.map((n) => (n.id === action.id ? { ...n, ...action.updates } : n)),
      };
    }
    case "REMOVE":
      return { ...state, notifications: state.notifications.filter((n) => n.id !== action.id) };
    case "SET_CONNECTED":
      return { ...state, connected: action.connected };
    case "SET_SERVICE_STATUS": {
      const statuses = [...state.serviceStatuses];
      const idx = statuses.findIndex((s) => s.service === action.status.service && s.account === action.status.account);
      if (idx >= 0) {
        statuses[idx] = action.status;
      } else {
        statuses.push(action.status);
      }
      return { ...state, serviceStatuses: statuses };
    }
    case "APPEND_OLDER": {
      const existingIds = new Set(state.notifications.map((n) => n.id));
      const newOnes = action.notifications.filter((n) => !existingIds.has(n.id));
      return { ...state, notifications: [...state.notifications, ...newOnes] };
    }
    default:
      return state;
  }
}

export function useNotifications() {
  const [state, dispatch] = useReducer(reducer, {
    notifications: [],
    serviceStatuses: [],
    connected: false,
  });
  const [activeFilter, setActiveFilter] = useState<Source | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const wsRef = useRef<ReturnType<typeof createWsClient> | null>(null);

  useEffect(() => {
    const client = createWsClient({
      onInitialLoad: (notifications) => dispatch({ type: "LOAD", notifications }),
      onNewNotification: (notification) => dispatch({ type: "ADD_OR_UPDATE", notification }),
      onNotificationUpdated: (id, updates) => dispatch({ type: "UPDATE_ONE", id, updates }),
      onNotificationRemoved: (id) => dispatch({ type: "REMOVE", id }),
      onConnectionStatus: (status) => dispatch({ type: "SET_SERVICE_STATUS", status }),
      onConnected: () => dispatch({ type: "SET_CONNECTED", connected: true }),
      onDisconnected: () => dispatch({ type: "SET_CONNECTED", connected: false }),
    });
    wsRef.current = client;
    client.connect();
    return () => client.disconnect();
  }, []);

  const filteredNotifications = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const result: Notification[] = [];
    for (const n of state.notifications) {
      if (n.triage_status === "archived") continue;
      if (activeFilter !== "all" && n.source !== activeFilter) continue;
      if (q && !n.title.toLowerCase().includes(q) && !n.body.toLowerCase().includes(q) && !n.sender_name.toLowerCase().includes(q)) continue;
      result.push(n);
    }
    const priorityOrder: Record<string, number> = { urgent: 0, high: 1, normal: 2, low: 3 };
    result.sort((a, b) => {
      const pDiff = (priorityOrder[a.priority] ?? 2) - (priorityOrder[b.priority] ?? 2);
      if (pDiff !== 0) return pDiff;
      return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
    });
    return result;
  }, [state.notifications, activeFilter, searchQuery]);

  const unreadCounts = useMemo(() => {
    const counts: Record<string, number> = { gmail: 0, outlook: 0, slack: 0, asana: 0, plane: 0, posthog: 0, total: 0 };
    for (const n of state.notifications) {
      if (n.triage_status === "unread") {
        counts[n.source] = (counts[n.source] || 0) + 1;
        counts.total++;
      }
    }
    return counts;
  }, [state.notifications]);

  const selectedNotification = useMemo(
    () => state.notifications.find((n) => n.id === selectedId) ?? null,
    [state.notifications, selectedId],
  );

  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const notificationCountRef = useRef(0);
  notificationCountRef.current = state.notifications.length;

  const markRead = useCallback((id: string) => {
    dispatch({ type: "UPDATE_ONE", id, updates: { triage_status: "read" } });
  }, []);

  const archive = useCallback((id: string) => {
    dispatch({ type: "UPDATE_ONE", id, updates: { triage_status: "archived" } });
  }, []);

  const actioned = useCallback((id: string) => {
    dispatch({ type: "UPDATE_ONE", id, updates: { triage_status: "actioned" } });
  }, []);

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const offset = notificationCountRef.current;
      const { notifications: older, has_more } = await getNotifications(50, undefined, offset);
      dispatch({ type: "APPEND_OLDER", notifications: older });
      setHasMore(has_more);
    } catch (e) {
      console.error("Failed to load more:", e);
    }
    setLoadingMore(false);
  }, [loadingMore, hasMore]);

  return {
    notifications: filteredNotifications,
    allNotifications: state.notifications,
    unreadCounts,
    serviceStatuses: state.serviceStatuses,
    connected: state.connected,
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
  };
}
