import { test, expect } from "@playwright/test";

test.describe("Backend API Health", () => {
  test("health endpoint returns ok", async ({ request }) => {
    const resp = await request.get("http://localhost:8070/health");
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body.status).toBe("ok");
  });

  test("settings endpoint returns data", async ({ request }) => {
    const resp = await request.get("http://localhost:8070/api/settings");
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body).toHaveProperty("stt_backend");
    expect(body).toHaveProperty("voice_shortcut");
  });

  test("triage endpoint returns array", async ({ request }) => {
    const resp = await request.get("http://localhost:8070/api/triage");
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(Array.isArray(body)).toBeTruthy();
  });

  test("morning brief endpoint returns data", async ({ request }) => {
    const resp = await request.get("http://localhost:8070/api/brief/morning");
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body).toHaveProperty("pending_total");
  });

  test("voice process endpoint accepts text", async ({ request }) => {
    const resp = await request.post("http://localhost:8070/api/voice/process", {
      data: { text: "what errors do I have" },
    });
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body).toHaveProperty("intent");
    expect(body).toHaveProperty("response");
  });

  test("stats endpoint returns data", async ({ request }) => {
    const resp = await request.get("http://localhost:8070/api/stats");
    expect(resp.ok()).toBeTruthy();
    const body = await resp.json();
    expect(body).toHaveProperty("weekly_resolved");
  });
});
