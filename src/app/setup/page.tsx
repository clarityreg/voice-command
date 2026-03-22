"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE } from "@/lib/api";
import { getAuthStatus } from "@/lib/notificationApi";

type Step = "welcome" | "connect" | "done";

export default function SetupPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("welcome");
  const [gmailConnected, setGmailConnected] = useState(false);
  const [outlookConnected, setOutlookConnected] = useState(false);

  const checkStatus = useCallback(async () => {
    try {
      const auth = await getAuthStatus();
      setGmailConnected(auth.gmail_accounts.some((a: { connected: boolean }) => a.connected));
      setOutlookConnected(auth.outlook_accounts.some((a: { connected: boolean }) => a.connected));
    } catch {
      // Backend not available yet
    }
  }, []);

  // Poll for connection status on the connect step
  useEffect(() => {
    if (step !== "connect") return;
    checkStatus();
    const interval = setInterval(checkStatus, 3000);
    return () => clearInterval(interval);
  }, [step, checkStatus]);

  const handleComplete = () => {
    localStorage.setItem("clarity-setup-complete", "true");
    router.push("/inbox");
  };

  return (
    <div className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center gap-6 text-center">
      {step === "welcome" && (
        <>
          <div className="text-5xl">🎯</div>
          <h1 className="text-2xl font-bold text-bark">Welcome to Clarity</h1>
          <p className="text-sm text-bark-muted leading-relaxed">
            Your ADHD-friendly command centre for triaging errors, vulnerabilities, and tasks.
            Connect your email accounts to get started.
          </p>
          <button
            onClick={() => setStep("connect")}
            className="rounded-pill bg-nav-bg px-8 py-3 text-sm font-medium text-cream transition hover:opacity-90"
          >
            Get Started
          </button>
        </>
      )}

      {step === "connect" && (
        <>
          <h1 className="text-2xl font-bold text-bark">Connect Accounts</h1>
          <p className="text-sm text-bark-muted">
            Link your email to see notifications in your inbox.
          </p>

          <div className="flex w-full flex-col gap-3">
            {/* Gmail */}
            <div className="flex items-center justify-between rounded-card bg-card-bg p-4 shadow-card">
              <div className="flex items-center gap-3">
                <span className="text-2xl">✉️</span>
                <div className="text-left">
                  <p className="font-semibold text-bark">Gmail</p>
                  <p className="text-xs text-bark-muted">
                    {gmailConnected ? "Connected" : "Not connected"}
                  </p>
                </div>
              </div>
              {gmailConnected ? (
                <span className="h-3 w-3 rounded-full bg-sev-low" />
              ) : (
                <a
                  href={`${API_BASE}/auth/google/start`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-pill bg-nav-bg px-4 py-2 text-sm font-medium text-cream hover:opacity-90"
                >
                  Connect
                </a>
              )}
            </div>

            {/* Outlook */}
            <div className="flex items-center justify-between rounded-card bg-card-bg p-4 shadow-card">
              <div className="flex items-center gap-3">
                <span className="text-2xl">📧</span>
                <div className="text-left">
                  <p className="font-semibold text-bark">Outlook</p>
                  <p className="text-xs text-bark-muted">
                    {outlookConnected ? "Connected" : "Not connected"}
                  </p>
                </div>
              </div>
              {outlookConnected ? (
                <span className="h-3 w-3 rounded-full bg-sev-low" />
              ) : (
                <a
                  href={`${API_BASE}/auth/microsoft/start`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-pill bg-nav-bg px-4 py-2 text-sm font-medium text-cream hover:opacity-90"
                >
                  Connect
                </a>
              )}
            </div>

            {/* Other integrations are configured via Settings */}
            <p className="text-xs text-bark-muted">
              Slack, Asana, and Plane can be configured in Settings.
            </p>
          </div>

          <div className="flex gap-4">
            <button
              onClick={() => setStep("done")}
              className="rounded-pill bg-nav-bg px-8 py-3 text-sm font-medium text-cream transition hover:opacity-90"
            >
              Continue
            </button>
            <button
              onClick={() => setStep("done")}
              className="text-sm text-bark-muted hover:text-bark"
            >
              Skip
            </button>
          </div>
        </>
      )}

      {step === "done" && (
        <>
          <div className="text-5xl">🎉</div>
          <h1 className="text-2xl font-bold text-bark">You&apos;re all set!</h1>
          <p className="text-sm text-bark-muted">
            Your inbox is ready. You can always connect more accounts in Settings.
          </p>
          <button
            onClick={handleComplete}
            className="rounded-pill bg-nav-bg px-8 py-3 text-sm font-medium text-cream transition hover:opacity-90"
          >
            Go to Inbox
          </button>
        </>
      )}
    </div>
  );
}
