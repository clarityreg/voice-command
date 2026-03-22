import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import InboxSidebar from "./InboxSidebar";

vi.mock("@/lib/notificationApi", () => ({
  syncEmails: vi.fn(),
}));

import { syncEmails } from "@/lib/notificationApi";

const mockSyncEmails = vi.mocked(syncEmails);

beforeEach(() => {
  vi.clearAllMocks();
});

const defaultProps = {
  activeFilter: "all" as const,
  onFilterChange: vi.fn(),
  unreadCounts: { total: 5, gmail: 3, slack: 2 },
  searchQuery: "",
  onSearchChange: vi.fn(),
};

describe("InboxSidebar", () => {
  it("renders search input", () => {
    render(<InboxSidebar {...defaultProps} />);
    expect(screen.getByPlaceholderText("Search...")).toBeInTheDocument();
  });

  it("calls onSearchChange when typing", () => {
    const onSearchChange = vi.fn();
    render(<InboxSidebar {...defaultProps} onSearchChange={onSearchChange} />);
    fireEvent.change(screen.getByPlaceholderText("Search..."), { target: { value: "test" } });
    expect(onSearchChange).toHaveBeenCalledWith("test");
  });

  it("renders filter buttons for all sources", () => {
    render(<InboxSidebar {...defaultProps} />);
    expect(screen.getByText("All")).toBeInTheDocument();
    expect(screen.getByText("Gmail")).toBeInTheDocument();
    expect(screen.getByText("Slack")).toBeInTheDocument();
    expect(screen.getByText("Plane")).toBeInTheDocument();
  });

  it("calls onFilterChange when filter button clicked", () => {
    const onFilterChange = vi.fn();
    render(<InboxSidebar {...defaultProps} onFilterChange={onFilterChange} />);
    fireEvent.click(screen.getByText("Gmail"));
    expect(onFilterChange).toHaveBeenCalledWith("gmail");
  });

  it("shows unread count badges", () => {
    render(<InboxSidebar {...defaultProps} />);
    expect(screen.getByText("5")).toBeInTheDocument(); // total
    expect(screen.getByText("3")).toBeInTheDocument(); // gmail
    expect(screen.getByText("2")).toBeInTheDocument(); // slack
  });

  it("syncs emails on button click", async () => {
    mockSyncEmails.mockResolvedValueOnce({ synced: 3, errors: [] });
    render(<InboxSidebar {...defaultProps} />);
    fireEvent.click(screen.getByText("↻ Sync Emails"));
    await waitFor(() => {
      expect(screen.getByText("3 synced")).toBeInTheDocument();
    });
    expect(mockSyncEmails).toHaveBeenCalled();
  });

  it("shows error on sync failure", async () => {
    mockSyncEmails.mockRejectedValueOnce(new Error("fail"));
    render(<InboxSidebar {...defaultProps} />);
    fireEvent.click(screen.getByText("↻ Sync Emails"));
    await waitFor(() => {
      expect(screen.getByText("Sync failed")).toBeInTheDocument();
    });
  });

  it("disables sync button while syncing", async () => {
    let resolveSync: (val: { synced: number; errors: string[] }) => void;
    mockSyncEmails.mockReturnValueOnce(
      new Promise((resolve) => { resolveSync = resolve; }),
    );
    render(<InboxSidebar {...defaultProps} />);
    fireEvent.click(screen.getByText("↻ Sync Emails"));
    expect(screen.getByText("Syncing...")).toBeDisabled();
    resolveSync!({ synced: 0, errors: [] });
    await waitFor(() => {
      expect(screen.queryByText("Syncing...")).not.toBeInTheDocument();
    });
  });
});
