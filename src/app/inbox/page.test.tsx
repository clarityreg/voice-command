import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import InboxPage from "./page";
import type { Notification } from "@/lib/notificationTypes";

vi.mock("@/lib/notificationApi", () => ({
  actionNotification: vi.fn(() => Promise.resolve()),
  archiveNotification: vi.fn(() => Promise.resolve()),
  markNotificationRead: vi.fn(() => Promise.resolve()),
}));

const mockSetActiveFilter = vi.fn();
const mockSetSearchQuery = vi.fn();
const mockSetSelectedId = vi.fn();
const mockMarkRead = vi.fn();
const mockArchive = vi.fn();
const mockActioned = vi.fn();
const mockLoadMore = vi.fn();

function makeNotification(overrides: Partial<Notification> = {}): Notification {
  return {
    id: "n1",
    source: "gmail",
    source_account: "test@gmail.com",
    source_id: "src-1",
    notification_type: "email",
    title: "Test Notification",
    body: "Test body",
    sender_name: "Alice",
    timestamp: new Date().toISOString(),
    priority: "normal",
    triage_status: "read",
    is_actionable: true,
    ...overrides,
  };
}

const defaultHookReturn = {
  notifications: [] as Notification[],
  unreadCounts: { total: 0 },
  connected: true,
  activeFilter: "all" as const,
  setActiveFilter: mockSetActiveFilter,
  searchQuery: "",
  setSearchQuery: mockSetSearchQuery,
  selectedNotification: null as Notification | null,
  setSelectedId: mockSetSelectedId,
  markRead: mockMarkRead,
  archive: mockArchive,
  actioned: mockActioned,
  loadMore: mockLoadMore,
  hasMore: false,
  loadingMore: false,
};

vi.mock("@/hooks/useNotifications", () => ({
  useNotifications: vi.fn(() => defaultHookReturn),
}));

import { useNotifications } from "@/hooks/useNotifications";
const mockUseNotifications = vi.mocked(useNotifications);

beforeEach(() => {
  vi.clearAllMocks();
  mockUseNotifications.mockReturnValue(defaultHookReturn);
});

describe("InboxPage", () => {
  it("renders empty state when no notifications", () => {
    render(<InboxPage />);
    expect(screen.getByText("No notifications")).toBeInTheDocument();
  });

  it("shows connecting message when not connected", () => {
    mockUseNotifications.mockReturnValue({ ...defaultHookReturn, connected: false });
    render(<InboxPage />);
    expect(screen.getByText("Connecting to backend...")).toBeInTheDocument();
  });

  it("renders notification cards", () => {
    const notifications = [
      makeNotification({ id: "n1", title: "First" }),
      makeNotification({ id: "n2", title: "Second" }),
    ];
    mockUseNotifications.mockReturnValue({ ...defaultHookReturn, notifications });
    render(<InboxPage />);
    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
  });

  it("shows Load More button when hasMore is true", () => {
    mockUseNotifications.mockReturnValue({
      ...defaultHookReturn,
      notifications: [makeNotification()],
      hasMore: true,
    });
    render(<InboxPage />);
    expect(screen.getByText("Load More")).toBeInTheDocument();
  });

  it("shows Loading... when loading more", () => {
    mockUseNotifications.mockReturnValue({
      ...defaultHookReturn,
      notifications: [makeNotification()],
      hasMore: true,
      loadingMore: true,
    });
    render(<InboxPage />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("renders detail panel with empty state", () => {
    render(<InboxPage />);
    expect(screen.getByText("Select a notification")).toBeInTheDocument();
  });

  it("renders mobile filter pills", () => {
    render(<InboxPage />);
    // Mobile pills include all source labels
    expect(screen.getAllByText("All").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Gmail").length).toBeGreaterThanOrEqual(1);
  });

  it("selects notification and marks unread as read", () => {
    const n = makeNotification({ id: "n1", triage_status: "unread" });
    mockUseNotifications.mockReturnValue({
      ...defaultHookReturn,
      notifications: [n],
    });
    render(<InboxPage />);

    // Click the notification card
    const cards = screen.getAllByRole("button");
    const cardBtn = cards.find((el) => el.textContent?.includes("Test Notification"));
    if (cardBtn) fireEvent.click(cardBtn);

    expect(mockSetSelectedId).toHaveBeenCalledWith("n1");
    expect(mockMarkRead).toHaveBeenCalledWith("n1");
  });

  it("handles archive from notification card", () => {
    const n = makeNotification({ id: "n1" });
    mockUseNotifications.mockReturnValue({
      ...defaultHookReturn,
      notifications: [n],
    });
    render(<InboxPage />);

    // Find the Archive button
    fireEvent.click(screen.getByText("Archive"));
    expect(mockArchive).toHaveBeenCalledWith("n1");
  });

  it("calls loadMore on button click", () => {
    mockUseNotifications.mockReturnValue({
      ...defaultHookReturn,
      notifications: [makeNotification()],
      hasMore: true,
    });
    render(<InboxPage />);
    fireEvent.click(screen.getByText("Load More"));
    expect(mockLoadMore).toHaveBeenCalled();
  });

  it("handles keyboard navigation j/k", () => {
    const notifications = [
      makeNotification({ id: "n1", title: "First" }),
      makeNotification({ id: "n2", title: "Second" }),
    ];
    mockUseNotifications.mockReturnValue({ ...defaultHookReturn, notifications });
    render(<InboxPage />);

    // Press j to select first
    fireEvent.keyDown(window, { key: "j" });
    expect(mockSetSelectedId).toHaveBeenCalled();
  });

  it("handles keyboard shortcut a for archive", () => {
    const n = makeNotification({ id: "n1" });
    mockUseNotifications.mockReturnValue({
      ...defaultHookReturn,
      notifications: [n],
      selectedNotification: n,
    });
    render(<InboxPage />);

    fireEvent.keyDown(window, { key: "a" });
    expect(mockArchive).toHaveBeenCalledWith("n1");
  });

  it("handles keyboard shortcut d for actioned", () => {
    const n = makeNotification({ id: "n1" });
    mockUseNotifications.mockReturnValue({
      ...defaultHookReturn,
      notifications: [n],
      selectedNotification: n,
    });
    render(<InboxPage />);

    fireEvent.keyDown(window, { key: "d" });
    expect(mockActioned).toHaveBeenCalledWith("n1");
  });

  it("handles keyboard shortcut t for task creator", () => {
    const n = makeNotification({ id: "n1" });
    mockUseNotifications.mockReturnValue({
      ...defaultHookReturn,
      notifications: [n],
      selectedNotification: n,
    });
    render(<InboxPage />);

    fireEvent.keyDown(window, { key: "t" });
    // Task creator modal should open — look for heading
    expect(screen.getAllByText("Create Task").length).toBeGreaterThanOrEqual(1);
  });

  it("handles Cmd+number for source filter", () => {
    render(<InboxPage />);
    fireEvent.keyDown(window, { key: "2", metaKey: true });
    expect(mockSetActiveFilter).toHaveBeenCalledWith("gmail");
  });

  it("ignores keyboard shortcuts when typing in input", () => {
    mockUseNotifications.mockReturnValue({
      ...defaultHookReturn,
      notifications: [makeNotification()],
      selectedNotification: makeNotification(),
    });
    render(<InboxPage />);

    // The search input is in InboxSidebar — simulate from an input element
    const event = new KeyboardEvent("keydown", { key: "a", bubbles: true });
    Object.defineProperty(event, "target", { value: document.createElement("input") });
    window.dispatchEvent(event);

    // Should NOT trigger archive since target is an input
    expect(mockArchive).not.toHaveBeenCalled();
  });

  it("shows waiting message when disconnected and no notifications", () => {
    mockUseNotifications.mockReturnValue({
      ...defaultHookReturn,
      connected: false,
      notifications: [],
    });
    render(<InboxPage />);
    expect(screen.getByText("Waiting for connection...")).toBeInTheDocument();
  });
});
