import { Page, expect } from "@playwright/test";

/** Wait for the backend health endpoint to respond. */
export async function waitForBackend(page: Page, timeout = 10000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    try {
      const resp = await page.request.get("http://localhost:8070/health");
      if (resp.ok()) return;
    } catch {
      // Not ready yet
    }
    await page.waitForTimeout(500);
  }
  throw new Error("Backend did not become healthy within timeout");
}

/** Navigate and wait for the page to be fully loaded. */
export async function navigateTo(page: Page, path: string) {
  await page.goto(path, { waitUntil: "networkidle" });
}

/** Assert that the sidebar navigation is visible. */
export async function expectSidebar(page: Page) {
  await expect(page.locator("text=Clarity").first()).toBeVisible();
  await expect(page.locator('a[href="/triage"]')).toBeVisible();
  await expect(page.locator('a[href="/settings"]')).toBeVisible();
}
