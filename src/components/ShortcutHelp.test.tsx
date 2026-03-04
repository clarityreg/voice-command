import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ShortcutHelp from "./ShortcutHelp";

describe("ShortcutHelp", () => {
  it("renders all shortcut keys", () => {
    render(<ShortcutHelp onClose={vi.fn()} />);
    expect(screen.getByText("c")).toBeInTheDocument();
    expect(screen.getByText("s")).toBeInTheDocument();
    expect(screen.getByText("d")).toBeInTheDocument();
    expect(screen.getByText("?")).toBeInTheDocument();
  });

  it("renders shortcut labels", () => {
    render(<ShortcutHelp onClose={vi.fn()} />);
    expect(screen.getByText("Create Issue")).toBeInTheDocument();
    expect(screen.getByText("Snooze")).toBeInTheDocument();
    expect(screen.getByText("Dismiss")).toBeInTheDocument();
  });

  // Close button calls onClose
  it("calls onClose when Close button is clicked", () => {
    const onClose = vi.fn();
    render(<ShortcutHelp onClose={onClose} />);
    fireEvent.click(screen.getByText("Close"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  // Clicking backdrop closes the modal
  it("calls onClose when backdrop is clicked", () => {
    const onClose = vi.fn();
    const { container } = render(<ShortcutHelp onClose={onClose} />);
    // Click the outer overlay div
    fireEvent.click(container.firstChild!);
    expect(onClose).toHaveBeenCalledOnce();
  });

  // Clicking modal content does not close
  it("does not call onClose when modal content is clicked", () => {
    const onClose = vi.fn();
    render(<ShortcutHelp onClose={onClose} />);
    fireEvent.click(screen.getByText("Keyboard Shortcuts"));
    expect(onClose).not.toHaveBeenCalled();
  });
});
