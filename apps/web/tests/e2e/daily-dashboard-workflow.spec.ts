import { expect, test } from "@playwright/test";
import { setMockApiScenario } from "./fixtures/apiMocks";
import { overviewSignalId } from "./fixtures/overviewFixtures";
import { demoWorkspaceId } from "./fixtures/workspaceFixtures";
import { expectNoForbiddenVisibleCopy } from "./helpers/safeText";

const populatedDailyRoutes = [
  { path: "/command-center", visibleText: /Command center ready/i },
  { path: "/brief", visibleText: /Daily brief/i },
  { path: "/data/onboarding", visibleText: /Data onboarding/i },
  { path: "/scanner", visibleText: /Scanner workflow/i },
  { path: "/triage", visibleText: /Setup triage/i },
  { path: `/signals/${overviewSignalId}`, visibleText: /Demo setup context is populated/i },
  { path: "/journal", visibleText: /Journal/i },
  { path: "/review/outcomes", visibleText: /Observed outcomes/i },
  { path: "/notifications", visibleText: /Review events/i },
  { path: "/quality", visibleText: /Quality dashboard/i },
] as const;

const optionalBackendRoutes = [
  "/command-center",
  "/brief",
  "/scanner",
  "/triage",
  "/journal",
  "/quality",
] as const;

test.describe("daily dashboard workflow smoke", () => {
  for (const route of populatedDailyRoutes) {
    test(`${route.path} renders populated demo workflow state`, async ({ page, request }) => {
      await setMockApiScenario(request, "daily-workflow-populated");
      const response = await page.goto(`${route.path}?workspaceId=${demoWorkspaceId}`);

      expect(response?.status() || 0).toBeLessThan(500);
      await expect(page.locator("body")).toBeVisible();
      await expect(page.getByText(/This page could not be found/i)).toHaveCount(0);
      await expect(page.getByText(route.visibleText).first()).toBeVisible();
      await expectNoForbiddenVisibleCopy(page);
    });
  }

  for (const route of optionalBackendRoutes) {
    test(`${route} renders when optional dashboard modules are missing`, async ({ page, request }) => {
      await setMockApiScenario(request, "overview-missing-sections");
      const response = await page.goto(`${route}?workspaceId=${demoWorkspaceId}`);

      expect(response?.status() || 0).toBeLessThan(500);
      await expect(page.locator("body")).toBeVisible();
      await expect(page.getByText(/This page could not be found/i)).toHaveCount(0);
      await expectNoForbiddenVisibleCopy(page);
    });
  }
});
