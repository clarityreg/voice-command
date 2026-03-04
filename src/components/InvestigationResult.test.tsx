import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import InvestigationResult from "./InvestigationResult";

const mockResult = {
  root_cause: "Database connection pool exhausted",
  affected_files: ["src/db/pool.py", "src/api/handler.py"],
  suggested_fix: "Add connection pool cleanup in the finally block",
  raw_response: "full raw text",
};

describe("InvestigationResult", () => {
  it("renders root cause, files, and suggested fix", () => {
    render(<InvestigationResult result={mockResult} onClose={() => {}} />);
    expect(screen.getByText("Database connection pool exhausted")).toBeInTheDocument();
    expect(screen.getByText("src/db/pool.py")).toBeInTheDocument();
    expect(screen.getByText("src/api/handler.py")).toBeInTheDocument();
    expect(screen.getByText(/Add connection pool cleanup/)).toBeInTheDocument();
  });

  it("hides affected files section when empty", () => {
    const noFiles = { ...mockResult, affected_files: [] };
    render(<InvestigationResult result={noFiles} onClose={() => {}} />);
    expect(screen.queryByText("Affected Files")).not.toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(<InvestigationResult result={mockResult} onClose={onClose} />);
    fireEvent.click(screen.getByText("Close"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("displays heading", () => {
    render(<InvestigationResult result={mockResult} onClose={() => {}} />);
    expect(screen.getByText("Investigation Result")).toBeInTheDocument();
  });
});
