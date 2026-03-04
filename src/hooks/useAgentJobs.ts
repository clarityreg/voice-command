"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";
import type { AgentJob, AgentEvent } from "@/lib/api";
import { getAgentJobs, approveAgentPlan, cancelAgentJob } from "@/lib/api";
import { createWsClient } from "@/lib/wsClient";

type State = {
  jobs: AgentJob[];
  activeEvents: Record<string, AgentEvent[]>;
  loading: boolean;
  error: string | null;
};

type Action =
  | { type: "SET_LOADING"; loading: boolean }
  | { type: "SET_ERROR"; error: string | null }
  | { type: "LOAD_JOBS"; jobs: AgentJob[] }
  | { type: "PREPEND_JOB"; job: AgentJob }
  | { type: "UPDATE_JOB"; job: AgentJob }
  | { type: "APPEND_EVENT"; jobId: string; event: AgentEvent };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_LOADING":
      return { ...state, loading: action.loading };
    case "SET_ERROR":
      return { ...state, error: action.error };
    case "LOAD_JOBS":
      return { ...state, jobs: action.jobs };
    case "PREPEND_JOB":
      return { ...state, jobs: [action.job, ...state.jobs] };
    case "UPDATE_JOB": {
      const idx = state.jobs.findIndex((j) => j.id === action.job.id);
      if (idx < 0) return state;
      const jobs = [...state.jobs];
      jobs[idx] = action.job;
      return { ...state, jobs };
    }
    case "APPEND_EVENT": {
      const existing = state.activeEvents[action.jobId] ?? [];
      return {
        ...state,
        activeEvents: {
          ...state.activeEvents,
          [action.jobId]: [...existing, action.event],
        },
      };
    }
    default:
      return state;
  }
}

export function useAgentJobs() {
  const [state, dispatch] = useReducer(reducer, {
    jobs: [],
    activeEvents: {},
    loading: true,
    error: null,
  });
  const wsRef = useRef<ReturnType<typeof createWsClient> | null>(null);

  useEffect(() => {
    getAgentJobs()
      .then((jobs) => {
        dispatch({ type: "LOAD_JOBS", jobs });
        dispatch({ type: "SET_LOADING", loading: false });
      })
      .catch(() => {
        dispatch({ type: "SET_ERROR", error: "Could not connect to backend. Is it running on :8070?" });
        dispatch({ type: "SET_LOADING", loading: false });
      });
  }, []);

  useEffect(() => {
    const client = createWsClient({
      onAgentJobCreated: (data) => {
        dispatch({ type: "PREPEND_JOB", job: data as unknown as AgentJob });
      },
      onAgentProgress: (data) => {
        const jobId = data.job_id as string;
        const event: AgentEvent = {
          type: (data.event_type as string) ?? "assistant",
          data: data as Record<string, unknown>,
          timestamp: (data.timestamp as string) ?? new Date().toISOString(),
        };
        dispatch({ type: "APPEND_EVENT", jobId, event });
      },
      onAgentPlanReady: (data) => {
        dispatch({ type: "UPDATE_JOB", job: data as unknown as AgentJob });
      },
      onAgentJobUpdated: (data) => {
        dispatch({ type: "UPDATE_JOB", job: data as unknown as AgentJob });
      },
      onAgentCompleted: (data) => {
        dispatch({ type: "UPDATE_JOB", job: data as unknown as AgentJob });
      },
      onAgentFailed: (data) => {
        dispatch({ type: "UPDATE_JOB", job: data as unknown as AgentJob });
      },
    });
    wsRef.current = client;
    client.connect();
    return () => client.disconnect();
  }, []);

  const approve = useCallback(async (jobId: string) => {
    const updated = await approveAgentPlan(jobId);
    dispatch({ type: "UPDATE_JOB", job: updated });
  }, []);

  const cancel = useCallback(async (jobId: string) => {
    const updated = await cancelAgentJob(jobId);
    dispatch({ type: "UPDATE_JOB", job: updated });
  }, []);

  return {
    jobs: state.jobs,
    activeEvents: state.activeEvents,
    approve,
    cancel,
    loading: state.loading,
    error: state.error,
  };
}
