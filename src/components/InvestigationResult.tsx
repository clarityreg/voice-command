"use client";

import type { InvestigationResult as InvestResult } from "@/lib/api";

interface Props {
  result: InvestResult;
  onClose: () => void;
}

export default function InvestigationResult({ result, onClose }: Props) {
  return (
    <div className="mt-3 rounded-card bg-cream-light p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-bold text-bark">Investigation Result</h3>
        <button
          onClick={onClose}
          className="text-xs text-bark-muted hover:text-bark"
        >
          Close
        </button>
      </div>

      <div className="flex flex-col gap-3 text-sm">
        <div>
          <span className="font-semibold text-bark">Root Cause</span>
          <p className="mt-1 text-bark-muted">{result.root_cause}</p>
        </div>

        {result.affected_files.length > 0 && (
          <div>
            <span className="font-semibold text-bark">Affected Files</span>
            <div className="mt-1 flex flex-wrap gap-1">
              {result.affected_files.map((file) => (
                <span key={file} className="rounded-pill bg-cream-dark px-2 py-0.5 text-xs text-bark">
                  {file}
                </span>
              ))}
            </div>
          </div>
        )}

        <div>
          <span className="font-semibold text-bark">Suggested Fix</span>
          <p className="mt-1 text-bark-muted">{result.suggested_fix}</p>
        </div>
      </div>
    </div>
  );
}
