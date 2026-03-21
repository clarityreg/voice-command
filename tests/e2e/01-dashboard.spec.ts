import { test, expect } from "@playwright/test";
import { navigateTo, expectSidebar } from "./helpers";

test.describe("Dashboard", () => {
  test("loads and renders main layout", async ({ page }) => {
    await navigateTo(page, "/");
    await expectSidebar(page);
    await expect(page.locator("text=Clarity").first()).toBeVisible();
  });

  test("shows morning brief section", async ({ page }) => {
    await navigateTo(page, "/");
    await expect(page.locator("text=Morning Brief")).toBeVisible();
  });

  test("shows voice command area with speak button", async ({ page }) => {
    await navigateTo(page, "/");
    await expect(page.locator("button", { hasText: "Speak" })).toBeVisible();
  });

  test("shows focus timer with start button", async ({ page }) => {
    await navigateTo(page, "/");
    await expect(page.locator("button", { hasText: "Start Focus" })).toBeVisible();
  });

  test("navigates to triage page via sidebar", async ({ page }) => {
    await navigateTo(page, "/");
    await page.click('a[href="/triage"]');
    await expect(page).toHaveURL(/\/triage/);
  });
});
