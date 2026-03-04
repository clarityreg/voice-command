import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TriageCard from "./TriageCard";
import type { TriageItem } from "@/lib/api";

const mockItem: TriageItem = {
  id: 1,
  source: "posthog",
  title: "TypeError: Cannot read property 'foo'",
  description: "Occurred on the dashboard page",
  severity: "critical",
  status: "pending",
  fingerprint: "abc123",
  occurrence_count: 5,
  first_seen: "2026-03-01T10:00:00Z",
  last_seen: "2026-03-03T12:00:00Z",
  metadata: {},
};

describe("TriageCard", () => {
  it("renders title and description", () => {
    render(
      <TriageCard item={mockItem} onSnooze={vi.fn()} onDismiss={vi.fn()} onCreateIssue={vi.fn()} />,
    );
    expect(screen.getByText(mockItem.title)).toBeInTheDocument();
    expect(screen.getByText(mockItem.description)).toBeInTheDocument();
  });

  it("shows severity badge", () => {
    render(
      <TriageCard item={mockItem} onSnooze={vi.fn()} onDismiss={vi.fn()} onCreateIssue={vi.fn()} />,
    );
    expect(screen.getByText("critical")).toBeInTheDocument();
  });

  it("shows source badge", () => {
    render(
      <TriageCard item={mockItem} onSnooze={vi.fn()} onDismiss={vi.fn()} onCreateIssue={vi.fn()} />,
    );
    expect(screen.getByText("posthog")).toBeInTheDocument();
  });

  it("shows occurrence count when > 1", () => {
    render(
      <TriageCard item={mockItem} onSnooze={vi.fn()} onDismiss={vi.fn()} onCreateIssue={vi.fn()} />,
    );
    expect(screen.getByText("5x")).toBeInTheDocument();
  });

  it("hides occurrence count when 1", () => {
    const singleItem = { ...mockItem, occurrence_count: 1 };
    render(
      <TriageCard item={singleItem} onSnooze={vi.fn()} onDismiss={vi.fn()} onCreateIssue={vi.fn()} />,
    );
    expect(screen.queryByText("1x")).not.toBeInTheDocument();
  });

  it("calls onCreateIssue when Create Issue is clicked", () => {
    const onCreateIssue = vi.fn();
    render(
      <TriageCard item={mockItem} onSnooze={vi.fn()} onDismiss={vi.fn()} onCreateIssue={onCreateIssue} />,
    );
    fireEvent.click(screen.getByText("Create Issue"));
    expect(onCreateIssue).toHaveBeenCalledWith(1);
  });

  it("calls onSnooze when Snooze is clicked", () => {
    const onSnooze = vi.fn();
    render(
      <TriageCard item={mockItem} onSnooze={onSnooze} onDismiss={vi.fn()} onCreateIssue={vi.fn()} />,
    );
    fireEvent.click(screen.getByText("Snooze"));
    expect(onSnooze).toHaveBeenCalledWith(1);
  });

  it("calls onDismiss when Dismiss is clicked", () => {
    const onDismiss = vi.fn();
    render(
      <TriageCard item={mockItem} onSnooze={vi.fn()} onDismiss={onDismiss} onCreateIssue={vi.fn()} />,
    );
    fireEvent.click(screen.getByText("Dismiss"));
    expect(onDismiss).toHaveBeenCalledWith(1);
  });

  it("shows Recurring badge when item is recurring", () => {
    const recurringItem = { ...mockItem, recurring: true };
    render(
      <TriageCard item={recurringItem} onSnooze={vi.fn()} onDismiss={vi.fn()} onCreateIssue={vi.fn()} />,
    );
    expect(screen.getByText("Recurring")).toBeInTheDocument();
  });

  it("hides Recurring badge when item is not recurring", () => {
    const normalItem = { ...mockItem, recurring: false };
    render(
      <TriageCard item={normalItem} onSnooze={vi.fn()} onDismiss={vi.fn()} onCreateIssue={vi.fn()} />,
    );
    expect(screen.queryByText("Recurring")).not.toBeInTheDocument();
  });
});
