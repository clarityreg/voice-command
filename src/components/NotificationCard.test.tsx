import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import NotificationCard from "./NotificationCard";
import type { Notification } from "@/lib/notificationTypes";

function makeNotification(overrides: Partial<Notification> = {}): Notification {
  return {
    id: "n1",
    source: "gmail",
    source_account: "test@gmail.com",
    source_id: "src-1",
    notification_type: "email",
    title: "Test Email",
    body: "This is a test email body",
    sender_name: "Alice",
    timestamp: new Date().toISOString(),
    priority: "normal",
    triage_status: "unread",
    is_actionable: true,
    ...overrides,
  };
}

describe("NotificationCard", () => {
  it("renders notification title and sender", () => {
    const n = makeNotification();
    render(
      <NotificationCard notification={n} isSelected={false} onSelect={vi.fn()} onArchive={vi.fn()} />,
    );
    expect(screen.getByText("Test Email")).toBeInTheDocument();
    expect(screen.getByText("Alice")).toBeInTheDocument();
  });

  it("calls onSelect when clicked", () => {
    const onSelect = vi.fn();
    const n = makeNotification();
    render(
      <NotificationCard notification={n} isSelected={false} onSelect={onSelect} onArchive={vi.fn()} />,
    );
    // The card itself has role="button" — get all and use the first one (the card wrapper)
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[0]);
    expect(onSelect).toHaveBeenCalledWith("n1");
  });

  it("calls onSelect on Enter key", () => {
    const onSelect = vi.fn();
    const n = makeNotification();
    render(
      <NotificationCard notification={n} isSelected={false} onSelect={onSelect} onArchive={vi.fn()} />,
    );
    const buttons = screen.getAllByRole("button");
    fireEvent.keyDown(buttons[0], { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith("n1");
  });

  it("shows bold text for unread notifications", () => {
    const n = makeNotification({ triage_status: "unread" });
    render(
      <NotificationCard notification={n} isSelected={false} onSelect={vi.fn()} onArchive={vi.fn()} />,
    );
    const titleEl = screen.getByText("Test Email");
    expect(titleEl.parentElement?.className).toContain("font-bold");
  });

  it("shows checkmark for actioned notifications", () => {
    const n = makeNotification({ triage_status: "actioned" });
    render(
      <NotificationCard notification={n} isSelected={false} onSelect={vi.fn()} onArchive={vi.fn()} />,
    );
    expect(screen.getByText("✓")).toBeInTheDocument();
  });

  it("shows priority dot for urgent emails", () => {
    const n = makeNotification({ priority: "urgent" });
    const { container } = render(
      <NotificationCard notification={n} isSelected={false} onSelect={vi.fn()} onArchive={vi.fn()} />,
    );
    const dot = container.querySelector(".rounded-full");
    expect(dot).toBeInTheDocument();
  });

  it("shows channel and project tags when present", () => {
    const n = makeNotification({ channel_name: "general", project_name: "My Project" });
    render(
      <NotificationCard notification={n} isSelected={false} onSelect={vi.fn()} onArchive={vi.fn()} />,
    );
    expect(screen.getByText("#general")).toBeInTheDocument();
    expect(screen.getByText("My Project")).toBeInTheDocument();
  });

  it("shows Actioned button for email sources with onActioned", () => {
    const onActioned = vi.fn();
    const n = makeNotification({ source: "gmail", triage_status: "unread" });
    render(
      <NotificationCard notification={n} isSelected={false} onSelect={vi.fn()} onArchive={vi.fn()} onActioned={onActioned} />,
    );
    const actionedBtn = screen.getByText("Actioned");
    fireEvent.click(actionedBtn);
    expect(onActioned).toHaveBeenCalledWith("n1");
  });

  it("does not show Actioned button for non-email sources", () => {
    const n = makeNotification({ source: "slack" });
    render(
      <NotificationCard notification={n} isSelected={false} onSelect={vi.fn()} onArchive={vi.fn()} onActioned={vi.fn()} />,
    );
    expect(screen.queryByText("Actioned")).not.toBeInTheDocument();
  });

  it("calls onArchive on Archive button click without triggering onSelect", () => {
    const onSelect = vi.fn();
    const onArchive = vi.fn();
    const n = makeNotification();
    render(
      <NotificationCard notification={n} isSelected={false} onSelect={onSelect} onArchive={onArchive} />,
    );
    fireEvent.click(screen.getByText("Archive"));
    expect(onArchive).toHaveBeenCalledWith("n1");
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("applies selected styling", () => {
    const n = makeNotification();
    const { container } = render(
      <NotificationCard notification={n} isSelected={true} onSelect={vi.fn()} onArchive={vi.fn()} />,
    );
    expect(container.firstChild).toHaveClass("ring-2");
  });

  it("renders body preview truncated", () => {
    const longBody = "A".repeat(200);
    const n = makeNotification({ body: longBody });
    render(
      <NotificationCard notification={n} isSelected={false} onSelect={vi.fn()} onArchive={vi.fn()} />,
    );
    // body is sliced to 120 chars
    expect(screen.getByText("A".repeat(120))).toBeInTheDocument();
  });
});
