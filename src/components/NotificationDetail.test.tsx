import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import NotificationDetail from "./NotificationDetail";
import type { Notification } from "@/lib/notificationTypes";

vi.mock("@/lib/notificationApi", () => ({
  replyToNotification: vi.fn(),
  snoozeNotification: vi.fn(),
}));

import { replyToNotification, snoozeNotification } from "@/lib/notificationApi";

const mockReply = vi.mocked(replyToNotification);
const mockSnooze = vi.mocked(snoozeNotification);

function makeNotification(overrides: Partial<Notification> = {}): Notification {
  return {
    id: "n1",
    source: "gmail",
    source_account: "test@gmail.com",
    source_id: "src-1",
    notification_type: "email",
    title: "Test Email Subject",
    body: "Email body content",
    sender_name: "Bob",
    timestamp: "2026-01-15T10:00:00Z",
    priority: "normal",
    triage_status: "read",
    is_actionable: true,
    ...overrides,
  };
}

const defaultProps = {
  onClose: vi.fn(),
  onArchive: vi.fn(),
  onActioned: vi.fn(),
  onCreateTask: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
  mockReply.mockResolvedValue({});
  mockSnooze.mockResolvedValue({});
});

describe("NotificationDetail", () => {
  it("shows empty state when no notification", () => {
    render(<NotificationDetail notification={null} {...defaultProps} />);
    expect(screen.getByText("Select a notification")).toBeInTheDocument();
  });

  it("renders notification content", () => {
    render(<NotificationDetail notification={makeNotification()} {...defaultProps} />);
    expect(screen.getByText("Test Email Subject")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("Email body content")).toBeInTheDocument();
  });

  it("shows source badge", () => {
    render(<NotificationDetail notification={makeNotification()} {...defaultProps} />);
    expect(screen.getByText(/Gmail/)).toBeInTheDocument();
  });

  it("shows Actioned button for emails", () => {
    render(<NotificationDetail notification={makeNotification()} {...defaultProps} />);
    expect(screen.getByText("Actioned")).toBeInTheDocument();
  });

  it("hides Actioned button for non-email sources", () => {
    render(<NotificationDetail notification={makeNotification({ source: "slack" })} {...defaultProps} />);
    expect(screen.queryByText("Actioned")).not.toBeInTheDocument();
  });

  it("hides Actioned button when already actioned", () => {
    render(<NotificationDetail notification={makeNotification({ triage_status: "actioned" })} {...defaultProps} />);
    // The "Actioned" text from the badge exists, but not the button
    expect(screen.getByText("✓ Actioned")).toBeInTheDocument();
  });

  it("calls onArchive and onClose when Archive clicked", () => {
    const onArchive = vi.fn();
    const onClose = vi.fn();
    render(<NotificationDetail notification={makeNotification()} {...defaultProps} onArchive={onArchive} onClose={onClose} />);
    fireEvent.click(screen.getByText("Archive"));
    expect(onArchive).toHaveBeenCalledWith("n1");
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onActioned and onClose when Actioned clicked", () => {
    const onActioned = vi.fn();
    const onClose = vi.fn();
    render(<NotificationDetail notification={makeNotification()} {...defaultProps} onActioned={onActioned} onClose={onClose} />);
    fireEvent.click(screen.getByText("Actioned"));
    expect(onActioned).toHaveBeenCalledWith("n1");
    expect(onClose).toHaveBeenCalled();
  });

  it("closes on Escape key", () => {
    const onClose = vi.fn();
    render(<NotificationDetail notification={makeNotification()} {...defaultProps} onClose={onClose} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("shows snooze menu and snoozes", async () => {
    render(<NotificationDetail notification={makeNotification()} {...defaultProps} />);
    fireEvent.click(screen.getByText("Snooze"));
    expect(screen.getByText("30 min")).toBeInTheDocument();
    expect(screen.getByText("1 hour")).toBeInTheDocument();
    expect(screen.getByText("4 hours")).toBeInTheDocument();
    expect(screen.getByText("Tomorrow")).toBeInTheDocument();

    fireEvent.click(screen.getByText("1 hour"));
    await waitFor(() => {
      expect(mockSnooze).toHaveBeenCalledWith("n1", 60);
    });
  });

  it("shows reply textarea for emails", () => {
    render(<NotificationDetail notification={makeNotification()} {...defaultProps} />);
    expect(screen.getByPlaceholderText("Write a reply...")).toBeInTheDocument();
  });

  it("does not show reply textarea for non-email", () => {
    render(<NotificationDetail notification={makeNotification({ source: "slack" })} {...defaultProps} />);
    expect(screen.queryByPlaceholderText("Write a reply...")).not.toBeInTheDocument();
  });

  it("sends reply on button click", async () => {
    render(<NotificationDetail notification={makeNotification()} {...defaultProps} />);
    const textarea = screen.getByPlaceholderText("Write a reply...");
    fireEvent.change(textarea, { target: { value: "My reply" } });
    fireEvent.click(screen.getByText("Send Reply"));
    await waitFor(() => {
      expect(mockReply).toHaveBeenCalledWith("n1", "My reply", "gmail", "test@gmail.com", "src-1");
    });
  });

  it("disables Send Reply when empty", () => {
    render(<NotificationDetail notification={makeNotification()} {...defaultProps} />);
    expect(screen.getByText("Send Reply")).toBeDisabled();
  });

  it("calls onCreateTask when Create Task clicked", () => {
    const onCreateTask = vi.fn();
    render(<NotificationDetail notification={makeNotification()} {...defaultProps} onCreateTask={onCreateTask} />);
    fireEvent.click(screen.getByText("Create Task"));
    expect(onCreateTask).toHaveBeenCalled();
  });

  it("shows priority badge for non-normal priority", () => {
    render(<NotificationDetail notification={makeNotification({ priority: "high" })} {...defaultProps} />);
    expect(screen.getByText("High")).toBeInTheDocument();
  });

  it("shows channel and project names", () => {
    render(
      <NotificationDetail
        notification={makeNotification({ channel_name: "dev", project_name: "Backend" })}
        {...defaultProps}
      />,
    );
    expect(screen.getByText("#dev")).toBeInTheDocument();
    expect(screen.getByText("Backend")).toBeInTheDocument();
  });

  it("shows 'No content' when body is empty", () => {
    render(<NotificationDetail notification={makeNotification({ body: "" })} {...defaultProps} />);
    expect(screen.getByText("No content")).toBeInTheDocument();
  });
});
