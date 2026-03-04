"use client";

import { useEffect, useState } from "react";
import {
  getThreshold,
  isPermissionGranted,
  requestPermission,
  setThreshold,
  type Severity,
} from "@/lib/notifications";

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low"];

export default function NotificationSettings() {
  const [threshold, setLocal] = useState<Severity>("high");
  const [permitted, setPermitted] = useState(false);

  useEffect(() => {
    setLocal(getThreshold());
    setPermitted(isPermissionGranted());
  }, []);

  const handlePermission = async () => {
    const granted = await requestPermission();
    setPermitted(granted);
  };

  const handleThresholdChange = (sev: Severity) => {
    setThreshold(sev);
    setLocal(sev);
  };

  return (
    <div className="rounded-card bg-card-bg p-4 shadow-card">
      <h3 className="mb-3 text-sm font-bold text-bark">Notifications</h3>

      {!permitted ? (
        <div className="flex items-center justify-between">
          <p className="text-sm text-bark-muted">
            Enable browser notifications for triage alerts.
          </p>
          <button
            onClick={handlePermission}
            className="rounded-pill bg-accent/20 px-4 py-2 text-sm font-medium text-accent hover:bg-accent/30"
          >
            Enable
          </button>
        </div>
      ) : (
        <div>
          <p className="mb-2 text-sm text-bark-muted">
            Notify me for items at or above:
          </p>
          <div className="flex gap-2">
            {SEVERITIES.map((sev) => (
              <button
                key={sev}
                onClick={() => handleThresholdChange(sev)}
                className={`rounded-pill px-3 py-1.5 text-xs font-medium capitalize transition ${
                  threshold === sev
                    ? "bg-nav-bg text-cream"
                    : "bg-cream-dark text-bark hover:bg-cream"
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
