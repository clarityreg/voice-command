import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import AgentPage from "./page";

vi.mock("@/hooks/useAgentJobs", () => ({
  useAgentJobs: vi.fn(),
}));

import { useAgentJobs } from "@/hooks/useAgentJobs";
const mockedUseAgentJobs = vi.mocked(useAgentJobs);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AgentPage", () => {
  it("shows empty state when no jobs exist", () => {
    mockedUseAgentJobs.mockReturnValue({
      jobs: [],
      activeEvents: {},
      approve: vi.fn(),
      cancel: vi.fn(),
      loading: false,
      error: null,
    });
    render(<AgentPage />);
    expect(screen.getByText(/No agent sessions yet/)).toBeInTheDocument();
  });

  it("renders job cards when jobs exist", () => {
    mockedUseAgentJobs.mockReturnValue({
      jobs: [
        {
          id: "job-1",
          triage_item_id: 5,
          status: "planning",
          plan_text: null,
          result_summary: null,
          branch_name: null,
          error_message: null,
          events_json: "[]",
          created_at: "2026-03-04T10:00:00Z",
          updated_at: "2026-03-04T10:00:00Z",
        },
      ],
      activeEvents: {},
      approve: vi.fn(),
      cancel: vi.fn(),
      loading: false,
      error: null,
    });
    render(<AgentPage />);
    expect(screen.getByText("Agent Activity")).toBeInTheDocument();
    expect(screen.getByText("Item #5")).toBeInTheDocument();
  });
});
