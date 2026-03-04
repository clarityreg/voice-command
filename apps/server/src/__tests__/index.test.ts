import { test, expect, beforeAll, afterAll, describe } from "bun:test";

const TEST_PORT = 4444;
let serverProcess: any;

beforeAll(async () => {
  // Start the server in a subprocess with a test port
  serverProcess = Bun.spawn(["bun", "run", "src/index.ts"], {
    cwd: import.meta.dir + "/../..",
    env: { ...process.env, SERVER_PORT: String(TEST_PORT) },
    stdout: "pipe",
    stderr: "pipe",
  });

  // Wait for the server to be ready
  const maxRetries = 30;
  for (let i = 0; i < maxRetries; i++) {
    try {
      const res = await fetch(`http://localhost:${TEST_PORT}/`);
      if (res.ok) break;
    } catch {
      // Server not ready yet
    }
    await Bun.sleep(200);
  }
});

afterAll(() => {
  if (serverProcess) {
    serverProcess.kill();
  }
});

const baseUrl = `http://localhost:${TEST_PORT}`;

// ---------------------------------------------------------------------------
// GET / (default response)
// ---------------------------------------------------------------------------
describe("GET /", () => {
  test("returns default text response", async () => {
    const res = await fetch(`${baseUrl}/`);
    expect(res.status).toBe(200);
    const text = await res.text();
    expect(text).toBe("Multi-Agent Observability Server");
  });
});

// ---------------------------------------------------------------------------
// OPTIONS (CORS preflight)
// ---------------------------------------------------------------------------
describe("OPTIONS /events", () => {
  test("returns CORS headers", async () => {
    const res = await fetch(`${baseUrl}/events`, { method: "OPTIONS" });
    expect(res.status).toBe(200);
    expect(res.headers.get("Access-Control-Allow-Origin")).toBe("*");
    expect(res.headers.get("Access-Control-Allow-Methods")).toContain("POST");
    expect(res.headers.get("Access-Control-Allow-Headers")).toContain(
      "Content-Type"
    );
  });
});

// ---------------------------------------------------------------------------
// POST /events
// ---------------------------------------------------------------------------
describe("POST /events", () => {
  test("valid event returns 200 with saved event containing id", async () => {
    const event = {
      source_app: "test-app",
      session_id: "test-session",
      hook_event_type: "PreToolUse",
      payload: { tool: "Bash" },
    };

    const res = await fetch(`${baseUrl}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(event),
    });

    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.id).toBeDefined();
    expect(typeof body.id).toBe("number");
    expect(body.source_app).toBe("test-app");
    expect(body.timestamp).toBeDefined();
  });

  test("missing required fields returns 400", async () => {
    const res = await fetch(`${baseUrl}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_app: "test-app" }), // missing session_id, hook_event_type, payload
    });

    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toBeDefined();
  });

  test("invalid JSON returns 400", async () => {
    const res = await fetch(`${baseUrl}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "not valid json {{{",
    });

    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// GET /events/recent
// ---------------------------------------------------------------------------
describe("GET /events/recent", () => {
  test("returns an array of events", async () => {
    const res = await fetch(`${baseUrl}/events/recent`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test("respects limit parameter", async () => {
    // Insert several events first
    for (let i = 0; i < 5; i++) {
      await fetch(`${baseUrl}/events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_app: "limit-test",
          session_id: "limit-session",
          hook_event_type: `Event-${i}`,
          payload: {},
        }),
      });
    }

    const res = await fetch(`${baseUrl}/events/recent?limit=2`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.length).toBeLessThanOrEqual(2);
  });
});

// ---------------------------------------------------------------------------
// GET /events/filter-options
// ---------------------------------------------------------------------------
describe("GET /events/filter-options", () => {
  test("returns FilterOptions shape", async () => {
    const res = await fetch(`${baseUrl}/events/filter-options`);
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.source_apps)).toBe(true);
    expect(Array.isArray(body.session_ids)).toBe(true);
    expect(Array.isArray(body.hook_event_types)).toBe(true);
  });
});

// ---------------------------------------------------------------------------
// POST /events/:id/respond (HITL)
// ---------------------------------------------------------------------------
describe("POST /events/:id/respond", () => {
  test("valid HITL response returns updated event", async () => {
    // First, insert an event with HITL data
    const createRes = await fetch(`${baseUrl}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_app: "hitl-test",
        session_id: "hitl-session",
        hook_event_type: "PermissionRequest",
        payload: { action: "write" },
        humanInTheLoop: {
          question: "Allow write?",
          responseWebSocketUrl: "ws://localhost:19999",
          type: "permission",
        },
      }),
    });

    const created = await createRes.json();
    const eventId = created.id;

    const res = await fetch(`${baseUrl}/events/${eventId}/respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        permission: true,
        hookEvent: created,
      }),
    });

    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.id).toBe(eventId);
    expect(body.humanInTheLoopStatus).toBeDefined();
    expect(body.humanInTheLoopStatus.status).toBe("responded");
  });

  test("non-existent event returns 404", async () => {
    const res = await fetch(`${baseUrl}/events/999999/respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        permission: false,
        hookEvent: {},
      }),
    });

    expect(res.status).toBe(404);
    const body = await res.json();
    expect(body.error).toContain("not found");
  });
});
