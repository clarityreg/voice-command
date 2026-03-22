/**
 * clarity-webhooks — Claude Code webhook receiver channel plugin
 *
 * Receives PostHog error alerts and Vercel deployment webhooks, formats them
 * into concise summaries, and forwards relevant events to the Clarity backend.
 *
 * Usage:
 *   bun run index.ts
 *
 * Environment variables:
 *   WEBHOOK_PORT     — port to listen on (default: 8787)
 *   CLARITY_API_URL  — Clarity backend base URL (default: http://localhost:8070)
 */

const PORT = Number(process.env.WEBHOOK_PORT ?? 8787);
const CLARITY_API_URL = process.env.CLARITY_API_URL ?? "http://localhost:8070";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PostHogEventProperty {
  $exception_type?: string;
  $exception_message?: string;
  $current_url?: string;
  $host?: string;
  $pathname?: string;
  distinct_id?: string;
  $session_id?: string;
  [key: string]: unknown;
}

interface PostHogWebhookPayload {
  event?: string;
  properties?: PostHogEventProperty;
  distinct_id?: string;
  timestamp?: string;
  // Alert-style wrapper (when PostHog sends an alert, not a raw event)
  alert?: {
    name?: string;
    threshold?: number;
    current_count?: number;
    window_minutes?: number;
  };
  data?: {
    event_count?: number;
    window?: string;
    [key: string]: unknown;
  };
}

interface VercelWebhookPayload {
  type?: string;
  payload?: {
    deployment?: {
      id?: string;
      url?: string;
      name?: string;
      state?: string;
      target?: string; // "production" | "preview"
      meta?: { githubCommitRef?: string; githubCommitMessage?: string };
    };
    project?: { name?: string };
    team?: { slug?: string };
    user?: { username?: string };
    url?: string;
  };
}

// ---------------------------------------------------------------------------
// Formatters
// ---------------------------------------------------------------------------

function formatPostHogEvent(body: PostHogWebhookPayload): string {
  const props = body.properties ?? {};

  const exceptionType = props.$exception_type ?? "UnknownError";
  const exceptionMessage = props.$exception_message ?? "(no message)";
  const url =
    props.$current_url ??
    (props.$host && props.$pathname
      ? `${props.$host}${props.$pathname}`
      : "unknown URL");
  const userId = props.distinct_id ?? body.distinct_id ?? "anonymous";
  const sessionId = props.$session_id ?? "—";

  // Occurrence info comes from alert metadata when PostHog fires an alert rule
  let occurrences = "";
  if (body.alert?.current_count !== undefined) {
    const window = body.alert.window_minutes
      ? `${body.alert.window_minutes} min`
      : "last window";
    occurrences = `\nOccurrences: ${body.alert.current_count} in ${window}`;
  } else if (body.data?.event_count !== undefined) {
    const window = body.data.window ?? "last window";
    occurrences = `\nOccurrences: ${body.data.event_count} in ${window}`;
  }

  return [
    `[PostHog Alert] ${exceptionType}: ${exceptionMessage}`,
    `URL: ${url}${occurrences}`,
    `User: ${userId}  Session: ${sessionId}`,
  ].join("\n");
}

function formatVercelEvent(body: VercelWebhookPayload): string {
  const eventType = body.type ?? "deployment.unknown";
  const dep = body.payload?.deployment;
  const project =
    body.payload?.project?.name ?? dep?.name ?? "unknown-project";
  const state = dep?.state ?? "unknown";
  const deployUrl = dep?.url ?? body.payload?.url ?? "—";
  const target = dep?.target ?? "preview";
  const branch = dep?.meta?.githubCommitRef ?? "—";
  const commitMsg = dep?.meta?.githubCommitMessage ?? "—";

  return [
    `[Vercel] ${eventType} — ${project} (${target})`,
    `State: ${state.toUpperCase()}  Branch: ${branch}`,
    `URL: ${deployUrl}`,
    `Commit: ${commitMsg}`,
  ].join("\n");
}

// ---------------------------------------------------------------------------
// Clarity backend forwarding
// ---------------------------------------------------------------------------

async function forwardToClarity(
  summary: string,
  source: "posthog" | "vercel",
  raw: unknown
): Promise<void> {
  const endpoint = `${CLARITY_API_URL}/api/triage`;

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source,
        summary,
        raw_payload: raw,
        received_at: new Date().toISOString(),
      }),
    });

    if (!res.ok) {
      console.warn(
        `[clarity-webhooks] Clarity triage endpoint returned ${res.status}: ${await res.text()}`
      );
    } else {
      console.log(`[clarity-webhooks] Forwarded to Clarity triage (${source})`);
    }
  } catch (err) {
    // Non-fatal — log and continue so PostHog still gets its 200 OK
    console.warn(
      `[clarity-webhooks] Failed to reach Clarity backend at ${endpoint}:`,
      err instanceof Error ? err.message : String(err)
    );
  }
}

// ---------------------------------------------------------------------------
// Channel output
//
// Printing to stdout is how Claude Code's channel system picks up events.
// We use a distinct prefix so the host can filter lines from this plugin.
// ---------------------------------------------------------------------------

function emit(summary: string): void {
  // Blank line before and after keeps the block readable in the terminal
  console.log("");
  for (const line of summary.split("\n")) {
    console.log(`[clarity-webhooks] ${line}`);
  }
  console.log("");
}

// ---------------------------------------------------------------------------
// Request handlers
// ---------------------------------------------------------------------------

async function handlePostHog(req: Request): Promise<Response> {
  let body: PostHogWebhookPayload;

  try {
    body = (await req.json()) as PostHogWebhookPayload;
  } catch {
    return new Response("Bad Request: invalid JSON", { status: 400 });
  }

  const eventType = body.event ?? "unknown";

  // Only emit a prominent alert for exception events; log everything else
  if (eventType === "$exception" || body.alert) {
    const summary = formatPostHogEvent(body);
    emit(summary);
    // Fire-and-forget — do not await so we respond quickly to PostHog
    forwardToClarity(summary, "posthog", body).catch(() => {
      /* already logged inside */
    });
  } else {
    console.log(
      `[clarity-webhooks] PostHog event received: ${eventType} (not an exception, skipping alert)`
    );
  }

  return new Response("OK", { status: 200 });
}

async function handleVercel(req: Request): Promise<Response> {
  let body: VercelWebhookPayload;

  try {
    body = (await req.json()) as VercelWebhookPayload;
  } catch {
    return new Response("Bad Request: invalid JSON", { status: 400 });
  }

  const summary = formatVercelEvent(body);
  emit(summary);

  // Only forward failed deployments to triage — success events are informational
  const state = body.payload?.deployment?.state ?? "";
  if (["ERROR", "FAILED", "CANCELED"].includes(state.toUpperCase())) {
    forwardToClarity(summary, "vercel", body).catch(() => {
      /* already logged inside */
    });
  }

  return new Response("OK", { status: 200 });
}

function handleHealth(): Response {
  return new Response(
    JSON.stringify({
      status: "ok",
      plugin: "clarity-webhooks",
      port: PORT,
      clarity_api_url: CLARITY_API_URL,
      timestamp: new Date().toISOString(),
    }),
    {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }
  );
}

// ---------------------------------------------------------------------------
// Server
// ---------------------------------------------------------------------------

const server = Bun.serve({
  port: PORT,

  async fetch(req) {
    const url = new URL(req.url);
    const method = req.method.toUpperCase();

    // Health check
    if (method === "GET" && url.pathname === "/health") {
      return handleHealth();
    }

    // PostHog webhook
    if (method === "POST" && url.pathname === "/webhook/posthog") {
      return handlePostHog(req);
    }

    // Vercel webhook
    if (method === "POST" && url.pathname === "/webhook/vercel") {
      return handleVercel(req);
    }

    return new Response("Not Found", { status: 404 });
  },

  error(err) {
    console.error("[clarity-webhooks] Server error:", err);
    return new Response("Internal Server Error", { status: 500 });
  },
});

console.log(
  `[clarity-webhooks] Listening on port ${server.port}`
);
console.log(
  `[clarity-webhooks] Clarity backend: ${CLARITY_API_URL}`
);
console.log(`[clarity-webhooks] Routes:`);
console.log(`  GET  /health`);
console.log(`  POST /webhook/posthog`);
console.log(`  POST /webhook/vercel`);
