import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import TaskCreatorModal from "./TaskCreatorModal";
import type { Notification } from "@/lib/notificationTypes";

vi.mock("@/lib/notificationApi", () => ({
  createTask: vi.fn(),
}));

import { createTask } from "@/lib/notificationApi";

const mockCreateTask = vi.mocked(createTask);

function makeNotification(): Notification {
  return {
    id: "n1",
    source: "gmail",
    source_account: "test@gmail.com",
    source_id: "src-1",
    notification_type: "email",
    title: "Bug report",
    body: "Something is broken",
    sender_name: "Alice",
    timestamp: "2026-01-15T10:00:00Z",
    priority: "normal",
    triage_status: "read",
    is_actionable: true,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockCreateTask.mockResolvedValue({ id: "t1" });
});

describe("TaskCreatorModal", () => {
  it("does not render when closed", () => {
    const { container } = render(
      <TaskCreatorModal isOpen={false} onClose={vi.fn()} />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders form when open", () => {
    render(<TaskCreatorModal isOpen={true} onClose={vi.fn()} />);
    // "Create Task" appears both as heading and button
    expect(screen.getAllByText("Create Task").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByPlaceholderText("Task title...")).toBeInTheDocument();
  });

  it("pre-fills from notification", () => {
    render(
      <TaskCreatorModal isOpen={true} onClose={vi.fn()} notification={makeNotification()} />,
    );
    expect(screen.getByDisplayValue("Bug report")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Something is broken")).toBeInTheDocument();
  });

  it("disables create button when title is empty", () => {
    render(<TaskCreatorModal isOpen={true} onClose={vi.fn()} />);
    const createBtns = screen.getAllByText("Create Task").filter((el) => el.tagName === "BUTTON");
    expect(createBtns[createBtns.length - 1]).toBeDisabled();
  });

  it("creates task on button click", async () => {
    render(<TaskCreatorModal isOpen={true} onClose={vi.fn()} />);
    fireEvent.change(screen.getByPlaceholderText("Task title..."), { target: { value: "New task" } });
    // The disabled "Create Task" button is now enabled after typing a title
    const createBtns = screen.getAllByText("Create Task").filter((el) => el.tagName === "BUTTON");
    fireEvent.click(createBtns[createBtns.length - 1]);
    await waitFor(() => {
      expect(mockCreateTask).toHaveBeenCalledWith(
        expect.objectContaining({ title: "New task", target: "plane", priority: "normal" }),
      );
    });
  });

  it("shows success message after creation", async () => {
    render(<TaskCreatorModal isOpen={true} onClose={vi.fn()} />);
    fireEvent.change(screen.getByPlaceholderText("Task title..."), { target: { value: "Done task" } });
    const createBtns = screen.getAllByText("Create Task").filter((el) => el.tagName === "BUTTON");
    fireEvent.click(createBtns[createBtns.length - 1]);
    await waitFor(() => {
      expect(screen.getByText(/Task created in Plane/)).toBeInTheDocument();
    });
  });

  it("calls onClose when Cancel clicked", () => {
    const onClose = vi.fn();
    render(<TaskCreatorModal isOpen={true} onClose={onClose} />);
    fireEvent.click(screen.getByText("Cancel"));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when Close clicked", () => {
    const onClose = vi.fn();
    render(<TaskCreatorModal isOpen={true} onClose={onClose} />);
    fireEvent.click(screen.getByText("Close"));
    expect(onClose).toHaveBeenCalled();
  });

  it("closes on Escape key", () => {
    const onClose = vi.fn();
    render(<TaskCreatorModal isOpen={true} onClose={onClose} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("allows changing target and priority", () => {
    render(<TaskCreatorModal isOpen={true} onClose={vi.fn()} />);
    const selects = screen.getAllByRole("combobox");
    // First select is target, second is priority
    fireEvent.change(selects[0], { target: { value: "asana" } });
    fireEvent.change(selects[1], { target: { value: "high" } });
    expect(selects[0]).toHaveValue("asana");
    expect(selects[1]).toHaveValue("high");
  });
});
