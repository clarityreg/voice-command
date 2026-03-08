import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import ConfirmationCard from "./ConfirmationCard";
import type { PendingAction } from "@/lib/api";

const createAction: PendingAction = {
  action_type: "create_task",
  project_id: "proj-1",
  project_name: "Acme Corp",
  title: "Fix login bug",
  priority: "urgent",
};

const completeAction: PendingAction = {
  action_type: "complete_task",
  project_id: "proj-1",
  project_name: "Acme Corp",
  task_ref: "ACME-42",
  sequence_id: 42,
};

let mockConfirm: () => void;
let mockReject: () => void;

beforeEach(() => {
  mockConfirm = vi.fn();
  mockReject = vi.fn();
  vi.useFakeTimers();
});

describe("ConfirmationCard", () => {
  it("renders create task details", () => {
    render(
      <ConfirmationCard
        action={createAction}
        onConfirm={mockConfirm}
        onReject={mockReject}
      />,
    );
    expect(screen.getByText("Create Task")).toBeInTheDocument();
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    expect(screen.getByText("Fix login bug")).toBeInTheDocument();
    expect(screen.getByText("urgent")).toBeInTheDocument();
  });

  it("renders complete task details", () => {
    render(
      <ConfirmationCard
        action={completeAction}
        onConfirm={mockConfirm}
        onReject={mockReject}
      />,
    );
    expect(screen.getByText("Complete Task")).toBeInTheDocument();
    expect(screen.getByText("ACME-42")).toBeInTheDocument();
  });

  it("calls onConfirm when Confirm button clicked", () => {
    render(
      <ConfirmationCard
        action={createAction}
        onConfirm={mockConfirm}
        onReject={mockReject}
      />,
    );
    fireEvent.click(screen.getByText(/Confirm/));
    expect(mockConfirm).toHaveBeenCalledOnce();
  });

  it("calls onReject when Reject button clicked", () => {
    render(
      <ConfirmationCard
        action={createAction}
        onConfirm={mockConfirm}
        onReject={mockReject}
      />,
    );
    fireEvent.click(screen.getByText(/Reject/));
    expect(mockReject).toHaveBeenCalledOnce();
  });

  it("calls onConfirm on Enter key", () => {
    render(
      <ConfirmationCard
        action={createAction}
        onConfirm={mockConfirm}
        onReject={mockReject}
      />,
    );
    fireEvent.keyDown(window, { key: "Enter" });
    expect(mockConfirm).toHaveBeenCalledOnce();
  });

  it("calls onReject on Escape key", () => {
    render(
      <ConfirmationCard
        action={createAction}
        onConfirm={mockConfirm}
        onReject={mockReject}
      />,
    );
    fireEvent.keyDown(window, { key: "Escape" });
    expect(mockReject).toHaveBeenCalledOnce();
  });

  it("auto-rejects after countdown expires", () => {
    render(
      <ConfirmationCard
        action={createAction}
        onConfirm={mockConfirm}
        onReject={mockReject}
      />,
    );
    // Advance 30 seconds one tick at a time so React processes each state update
    for (let i = 0; i < 31; i++) {
      act(() => {
        vi.advanceTimersByTime(1000);
      });
    }
    expect(mockReject).toHaveBeenCalled();
  });

  it("shows countdown timer", () => {
    render(
      <ConfirmationCard
        action={createAction}
        onConfirm={mockConfirm}
        onReject={mockReject}
      />,
    );
    expect(screen.getByText("30s")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByText("29s")).toBeInTheDocument();
  });

  it("does not show priority when set to none", () => {
    const noPriorityAction: PendingAction = {
      ...createAction,
      priority: "none",
    };
    render(
      <ConfirmationCard
        action={noPriorityAction}
        onConfirm={mockConfirm}
        onReject={mockReject}
      />,
    );
    expect(screen.queryByText("Priority")).not.toBeInTheDocument();
  });
});
