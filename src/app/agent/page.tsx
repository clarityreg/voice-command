"use client";

import { useAgentJobs } from "@/hooks/useAgentJobs";
import AgentJobCard from "@/components/AgentJobCard";

const ACTIVE_STATUSES = new Set(["planning", "plan_ready", "approved", "running"]);

export default function AgentPage() {
  const { jobs, activeEvents, approve, cancel, loading, error } = useAgentJobs();

  if (loading) {
    return (
      <div className="py-20 text-center text-bark-muted">
        Loading agent sessions...
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-20 text-center">
        <p className="text-sev-critical">{error}</p>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="py-20 text-center">
        <p className="text-bark-muted">
          No agent sessions yet. Fix an item from the Triage page to start.
        </p>
      </div>
    );
  }

  const activeJobs = jobs.filter((j) => ACTIVE_STATUSES.has(j.status));
  const doneJobs = jobs.filter((j) => !ACTIVE_STATUSES.has(j.status));

  return (
    <div className="mx-auto max-w-3xl">
      <h2 className="mb-4 text-xl font-bold text-bark">Agent Activity</h2>

      {activeJobs.length > 0 && (
        <div className="mb-6 space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-bark-muted">Active</h3>
          {activeJobs.map((job) => (
            <AgentJobCard
              key={job.id}
              job={job}
              events={activeEvents[job.id] ?? []}
              onApprove={approve}
              onCancel={cancel}
            />
          ))}
        </div>
      )}

      {doneJobs.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-bark-muted">Completed</h3>
          {doneJobs.map((job) => (
            <AgentJobCard
              key={job.id}
              job={job}
              events={activeEvents[job.id] ?? []}
              onApprove={approve}
              onCancel={cancel}
            />
          ))}
        </div>
      )}
    </div>
  );
}
