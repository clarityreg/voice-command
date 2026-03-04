"use client";

import { useCallback, useEffect, useState } from "react";
import { getAuthStatus, getServiceStatuses, removeGmailAccount, removeOutlookAccount } from "@/lib/notificationApi";
import type { ServiceStatus } from "@/lib/notificationTypes";
import { API_BASE } from "@/lib/api";

export default function AccountManager() {
  const [gmailAccounts, setGmailAccounts] = useState<{ email: string; connected: boolean }[]>([]);
  const [outlookAccounts, setOutlookAccounts] = useState<{ email: string; connected: boolean }[]>([]);
  const [serviceStatuses, setServiceStatuses] = useState<ServiceStatus[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [auth, services] = await Promise.all([getAuthStatus(), getServiceStatuses()]);
      setGmailAccounts(auth.gmail_accounts);
      setOutlookAccounts(auth.outlook_accounts);
      setServiceStatuses(services.services);
    } catch {
      // Service may not be configured
    }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleRemoveGmail = async (email: string) => {
    await removeGmailAccount(email);
    refresh();
  };

  const handleRemoveOutlook = async (email: string) => {
    await removeOutlookAccount(email);
    refresh();
  };

  if (loading) return <div className="animate-pulse rounded-card bg-cream-dark p-4">Loading accounts...</div>;

  return (
    <div className="flex flex-col gap-4">
      {/* Gmail */}
      <section className="rounded-card bg-card-bg p-5 shadow-card">
        <h3 className="mb-3 flex items-center gap-2 font-semibold text-bark">
          <span className="text-lg">✉️</span> Gmail Accounts
        </h3>
        {gmailAccounts.length === 0 ? (
          <p className="mb-2 text-sm text-bark-muted">No Gmail accounts connected.</p>
        ) : (
          <ul className="mb-2 flex flex-col gap-2">
            {gmailAccounts.map((a) => (
              <li key={a.email} className="flex items-center justify-between rounded-lg bg-cream-light px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${a.connected ? "bg-sev-low" : "bg-sev-critical"}`} />
                  <span className="text-sm font-medium text-bark">{a.email}</span>
                </div>
                <button onClick={() => handleRemoveGmail(a.email)} className="text-xs text-sev-critical hover:underline">
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
        <a href={`${API_BASE}/auth/google/start`} target="_blank" rel="noopener noreferrer" className="inline-block rounded-pill bg-nav-bg px-4 py-2 text-sm font-medium text-cream hover:opacity-90">
          Add Gmail Account
        </a>
      </section>

      {/* Outlook */}
      <section className="rounded-card bg-card-bg p-5 shadow-card">
        <h3 className="mb-3 flex items-center gap-2 font-semibold text-bark">
          <span className="text-lg">📧</span> Outlook Accounts
        </h3>
        {outlookAccounts.length === 0 ? (
          <p className="mb-2 text-sm text-bark-muted">No Outlook accounts connected.</p>
        ) : (
          <ul className="mb-2 flex flex-col gap-2">
            {outlookAccounts.map((a) => (
              <li key={a.email} className="flex items-center justify-between rounded-lg bg-cream-light px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${a.connected ? "bg-sev-low" : "bg-sev-critical"}`} />
                  <span className="text-sm font-medium text-bark">{a.email}</span>
                </div>
                <button onClick={() => handleRemoveOutlook(a.email)} className="text-xs text-sev-critical hover:underline">
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
        <a href={`${API_BASE}/auth/microsoft/start`} target="_blank" rel="noopener noreferrer" className="inline-block rounded-pill bg-nav-bg px-4 py-2 text-sm font-medium text-cream hover:opacity-90">
          Add Outlook Account
        </a>
      </section>

      {/* Service statuses */}
      <section className="rounded-card bg-card-bg p-5 shadow-card">
        <h3 className="mb-3 flex items-center gap-2 font-semibold text-bark">
          <span className="text-lg">📡</span> Service Status
        </h3>
        {serviceStatuses.length === 0 ? (
          <p className="text-sm text-bark-muted">No services configured.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {serviceStatuses.map((s, i) => (
              <li key={i} className="flex items-center gap-2 text-sm">
                <span className={`h-2 w-2 rounded-full ${s.connected ? "bg-sev-low" : "bg-sev-critical"}`} />
                <span className="font-medium text-bark capitalize">{s.service}</span>
                <span className="text-bark-light">{s.account}</span>
                <span className="text-bark-muted">{s.connected ? "Connected" : "Disconnected"}</span>
              </li>
            ))}
          </ul>
        )}
        <button onClick={refresh} className="mt-3 rounded-pill bg-cream-dark px-4 py-2 text-sm font-medium text-bark hover:opacity-80">
          Refresh
        </button>
      </section>
    </div>
  );
}
