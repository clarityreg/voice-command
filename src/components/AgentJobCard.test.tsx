import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import AgentJobCard from "./AgentJobCard";
import type { AgentJob } from "@/lib/api";

const mockJob: AgentJob = {
  id: "job-1",
  triage_item_id: 42,
  status: "planning",
  plan_text: null,
  result_summary: null,
  branch_name: null,
  error_message: null,
  events_json: "[]",
  created_at: "2026-03-04T10:00:00Z",
  updated_at: "2026-03-04T10:00:00Z",
};

describe("AgentJobCard", () => {
  it("renders status badge", () => {
    render(<AgentJobCard job={mockJob} events={[]} onApprove={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByText("planning")).toBeInTheDocument();
  });

  it("shows approve button when plan_ready", () => {
    const planReadyJob: AgentJob = {
      ...mockJob,
      status: "plan_ready",
      plan_text: "Fix the bug by updating the error handler.",
    };
    render(<AgentJobCard job={planReadyJob} events={[]} onApprove={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByText("Approve Fix")).toBeInTheDocument();
  });

  it("hides approve button when running", () => {
    const runningJob: AgentJob = { ...mockJob, status: "running" };
    render(<AgentJobCard job={runningJob} events={[]} onApprove={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.queryByText("Approve Fix")).not.toBeInTheDocument();
  });
});
