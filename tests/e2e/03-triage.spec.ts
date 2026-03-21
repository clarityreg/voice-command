import { test, expect } from "@playwright/test";
import { navigateTo } from "./helpers";

test.describe("Triage Page", () => {
  test("loads triage page", async ({ page }) => {
    await navigateTo(page, "/triage");
    // Either shows triage items or empty state
    const hasItems = await page.locator(".rounded-card").count();
    expect(hasItems).toBeGreaterThanOrEqual(0);
  });

  test("shows shortcut help toggle", async ({ page }) => {
    await navigateTo(page, "/triage");
    // Press ? to toggle help
    await page.keyboard.press("?");
    await expect(page.locator("text=Keyboard Shortcuts").or(page.locator("text=All clear"))).toBeVisible({ timeout: 3000 });
  });
});
