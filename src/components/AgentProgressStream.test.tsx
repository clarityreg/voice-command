import { describe, it, expect, vi, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import AgentProgressStream from "./AgentProgressStream";
import type { AgentEvent } from "@/lib/api";

beforeAll(() => {
  // jsdom doesn't implement scrollIntoView
  Element.prototype.scrollIntoView = vi.fn();
});

function makeEvent(type: string, data: Record<string, unknown> = {}): AgentEvent {
  return { type, data, timestamp: new Date().toISOString() };
}

describe("AgentProgressStream", () => {
  it("returns null for empty events", () => {
    const { container } = render(<AgentProgressStream events={[]} />);
    expect(container.innerHTML).toBe("");
  });

  it("renders assistant/text events", () => {
    const events = [makeEvent("assistant", { text: "Analyzing the code..." })];
    render(<AgentProgressStream events={events} />);
    expect(screen.getByText("Analyzing the code...")).toBeInTheDocument();
  });

  it("renders text event with content field", () => {
    const events = [makeEvent("text", { content: "Processing..." })];
    render(<AgentProgressStream events={events} />);
    expect(screen.getByText("Processing...")).toBeInTheDocument();
  });

  it("renders tool_use events with name and input", () => {
    const events = [makeEvent("tool_use", { name: "read_file", input: { path: "/src/app.ts" } })];
    render(<AgentProgressStream events={events} />);
    expect(screen.getByText("read_file")).toBeInTheDocument();
  });

  it("truncates long tool_use input", () => {
    const longInput = { data: "x".repeat(200) };
    const events = [makeEvent("tool_use", { name: "search", input: longInput })];
    render(<AgentProgressStream events={events} />);
    expect(screen.getByText(/…$/)).toBeInTheDocument();
  });

  it("renders tool_result events", () => {
    const events = [makeEvent("tool_result", { content: "File contents here" })];
    render(<AgentProgressStream events={events} />);
    expect(screen.getByText("File contents here")).toBeInTheDocument();
  });

  it("truncates long tool_result content", () => {
    const events = [makeEvent("tool_result", { content: "A".repeat(300) })];
    render(<AgentProgressStream events={events} />);
    expect(screen.getByText(/…$/)).toBeInTheDocument();
  });

  it("handles unknown event types gracefully", () => {
    const events = [makeEvent("unknown_type", { data: "test" })];
    const { container } = render(<AgentProgressStream events={events} />);
    // Should render the container but no event content
    expect(container.querySelector(".max-h-64")).toBeInTheDocument();
  });
});
