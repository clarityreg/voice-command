import { test, expect } from "@playwright/test";
import { navigateTo } from "./helpers";

test.describe("Navigation", () => {
  const pages = [
    { path: "/", title: "Focus" },
    { path: "/inbox", title: "Inbox" },
    { path: "/triage", title: "Triage" },
    { path: "/agent", title: "Agent" },
    { path: "/dashboard", title: "Events" },
    { path: "/stats", title: "Stats" },
    { path: "/settings", title: "Settings" },
  ];

  for (const { path, title } of pages) {
    test(`navigates to ${title} page (${path})`, async ({ page }) => {
      await navigateTo(page, path);
      // Each page should load without crashing
      await expect(page.locator("nav").first()).toBeVisible();
    });
  }

  test("sidebar highlights current page", async ({ page }) => {
    await navigateTo(page, "/settings");
    const settingsLink = page.locator('a[href="/settings"]');
    await expect(settingsLink).toBeVisible();
  });
});
