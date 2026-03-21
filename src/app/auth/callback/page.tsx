"use client";

/**
 * OAuth callback page.
 *
 * The backend redirects here after OAuth completes:
 *   http://localhost:3080/auth/callback?provider=gmail&email=user@gmail.com&status=success
 *   http://localhost:3080/auth/callback?provider=gmail&status=error&message=Access+denied
 *
 * Success: shows a confirmation card, then navigates to /settings after 3 s.
 * Error:   shows an error card with a "Try Again" button that returns to /settings.
 */

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function OAuthCallbackContent() {
  const router = useRouter();
  const params = useSearchParams();

  const provider = params.get("provider") ?? "provider";
  const email = params.get("email") ?? "";
  const status = params.get("status");
  const message = params.get("message") ?? "Something went wrong. Please try again.";

  const isSuccess = status === "success";

  // Auto-navigate to settings after 3 s on success.
  useEffect(() => {
    if (!isSuccess) return;
    const timer = setTimeout(() => router.push("/settings"), 3000);
    return () => clearTimeout(timer);
  }, [isSuccess, router]);

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="rounded-card bg-card-bg p-6 shadow-card w-full max-w-sm text-center">
        {isSuccess ? (
          <>
            {/* Success icon */}
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-sev-low/15">
              <svg
                aria-hidden="true"
                className="h-6 w-6 text-sev-low"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>

            <h1 className="mb-1 text-lg font-bold text-bark">
              {capitalize(provider)} connected
            </h1>

            {email && (
              <p className="mb-1 text-sm text-sev-low font-medium break-all">{email}</p>
            )}

            <p className="mt-3 text-xs text-bark-muted">
              Redirecting to Settings in 3 seconds&hellip;
            </p>
          </>
        ) : (
          <>
            {/* Error icon */}
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-sev-critical/15">
              <svg
                aria-hidden="true"
                className="h-6 w-6 text-sev-critical"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>

            <h1 className="mb-1 text-lg font-bold text-bark">Connection failed</h1>

            <p className="mb-5 text-sm text-sev-critical break-words">{message}</p>

            <button
              onClick={() => router.push("/settings")}
              className="rounded-pill bg-nav-bg px-5 py-2.5 text-sm font-medium text-cream transition hover:opacity-90"
            >
              Try Again
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <div className="rounded-card bg-card-bg p-6 shadow-card w-full max-w-sm text-center">
            <p className="text-sm text-bark-muted">Loading&hellip;</p>
          </div>
        </div>
      }
    >
      <OAuthCallbackContent />
    </Suspense>
  );
}
