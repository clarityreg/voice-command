"use client";

interface AgentPlanReviewProps {
  planText: string;
  onApprove: () => void;
  onCancel: () => void;
  approving?: boolean;
}

export default function AgentPlanReview({ planText, onApprove, onCancel, approving }: AgentPlanReviewProps) {
  return (
    <div className="rounded-card border border-cream-dark bg-cream p-4">
      <h4 className="mb-2 text-sm font-semibold text-bark">Proposed Fix Plan</h4>
      <pre className="mb-4 whitespace-pre-wrap text-sm text-bark-muted">{planText}</pre>
      <div className="flex gap-2">
        <button
          onClick={onApprove}
          disabled={approving}
          className="rounded-pill bg-sev-low px-4 py-2 text-sm font-medium text-cream transition hover:opacity-90 disabled:opacity-50"
        >
          {approving ? "Approving..." : "Approve Fix"}
        </button>
        <button
          onClick={onCancel}
          className="rounded-pill bg-cream px-4 py-2 text-sm font-medium text-bark transition hover:bg-cream-dark"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
