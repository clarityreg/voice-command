import { test, expect } from "@playwright/test";
import { navigateTo } from "./helpers";

test.describe("Settings Page", () => {
  test("loads settings form with all sections", async ({ page }) => {
    await navigateTo(page, "/settings");
    await expect(page.locator("h2", { hasText: "Settings" })).toBeVisible();
    await expect(page.locator("text=Plane Integration")).toBeVisible();
    await expect(page.locator("text=Voice Recognition")).toBeVisible();
    await expect(page.locator("text=PostHog")).toBeVisible();
  });

  test("shows voice shortcut recorder", async ({ page }) => {
    await navigateTo(page, "/settings");
    await expect(page.locator("text=Voice Shortcut")).toBeVisible();
    await expect(page.locator("text=Click to change")).toBeVisible();
  });

  test("shows save and reset buttons", async ({ page }) => {
    await navigateTo(page, "/settings");
    await expect(page.locator("button", { hasText: "Save Settings" })).toBeVisible();
    await expect(page.locator("button", { hasText: "Reset" })).toBeVisible();
  });

  test("shows connected accounts section", async ({ page }) => {
    await navigateTo(page, "/settings");
    await expect(page.locator("text=Gmail Accounts")).toBeVisible();
    await expect(page.locator("text=Outlook Accounts")).toBeVisible();
    await expect(page.locator("text=Service Status")).toBeVisible();
  });

  test("can update a text field and save", async ({ page }) => {
    await navigateTo(page, "/settings");
    // Wait for form to load
    const workspaceInput = page.locator('input').nth(1); // workspace slug field
    await workspaceInput.waitFor();
    await workspaceInput.fill("test-workspace");
    await page.click("button:has-text('Save Settings')");
    // Should show saved confirmation
    await expect(page.locator("text=Saved")).toBeVisible({ timeout: 5000 });
  });
});
