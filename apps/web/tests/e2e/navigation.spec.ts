import { expect, test } from "@playwright/test";
import { setMockApiScenario } from "./fixtures/apiMocks";
import { demoWorkspaceId } from "./fixtures/workspaceFixtures";
import { shellLinks } from "./helpers/selectors";

const existingRoutes = [
  "/onboarding",
  "/command-center",
  "/brief",
  "/data/onboarding",
  "/scanner",
  "/triage",
  "/journal",
  "/review/outcomes",
  "/preferences/strategy",
] as const;

test.describe("daily workflow navigation smoke", () => {
  test("app shell navigation renders core workflow links", async ({ page, request }) => {
    await setMockApiScenario(request, "ready-overview");
    await page.goto(`/command-center?workspaceId=${demoWorkspaceId}`);

    await expect(page.getByRole("link", { name: shellLinks.onboarding }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: shellLinks.commandCenter }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: shellLinks.brief }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: shellLinks.dataOnboarding }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: shellLinks.scanner }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: shellLinks.triage }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: shellLinks.journal }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: shellLinks.reviewOutcomes }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: shellLinks.preferences }).first()).toBeVisible();
  });

  for (const route of existingRoutes) {
    test(`${route} renders with mocked optional endpoints`, async ({ page, request }) => {
      await setMockApiScenario(request, "ready-overview");
      const response = await page.goto(`${route}?workspaceId=${demoWorkspaceId}`);
      expect(response?.status() || 0).toBeLessThan(500);
      await expect(page.locator("body")).toBeVisible();
      await expect(page.getByText(/This page could not be found/i)).toHaveCount(0);
    });
  }
});
