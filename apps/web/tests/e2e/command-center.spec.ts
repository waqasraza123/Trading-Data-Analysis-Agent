import { expect, test } from "@playwright/test";
import { setMockApiScenario } from "./fixtures/apiMocks";
import { demoWorkspaceId } from "./fixtures/workspaceFixtures";
import { expectNoForbiddenVisibleCopy } from "./helpers/safeText";

test.describe("command center smoke", () => {
  test("incomplete setup shows readiness gate and tolerates overview failure", async ({ page, request }) => {
    await setMockApiScenario(request, "command-incomplete");
    await page.goto(`/command-center?workspaceId=${demoWorkspaceId}`);

    await expect(page.getByRole("heading", { name: /Demo Analysis Workspace/i })).toBeVisible();
    await expect(page.getByText(/Data setup needed/i)).toBeVisible();
    await expect(page.getByRole("link", { name: /Open onboarding/i })).toBeVisible();
    await expect(page.getByText(/Backend unavailable|Workspace overview/i)).toBeVisible();
    await expectNoForbiddenVisibleCopy(page);
  });

  test("ready overview renders command-center daily sections and safe quick actions", async ({ page, request }) => {
    await setMockApiScenario(request, "ready-overview");
    await page.goto(`/command-center?workspaceId=${demoWorkspaceId}`);

    await expect(page.getByText(/Command center ready/i).first()).toBeVisible();
    await expect(page.getByText(/^Readiness$/i).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: /Review First/i }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: /Needs Confirmation/i }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: /Avoid Conditions/i }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: /Outcome Updates/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /Workflow Status/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Run deterministic daily workflow/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Generate brief/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /Refresh status/i })).toBeVisible();
    await expectNoForbiddenVisibleCopy(page);
  });

  test("quick action success shows returned result without hidden navigation", async ({ page, request }) => {
    await setMockApiScenario(request, "ready-overview");
    await page.goto(`/command-center?workspaceId=${demoWorkspaceId}`);

    await page.getByRole("button", { name: /Run deterministic daily workflow/i }).click();

    await expect(page.getByText(/Deterministic daily workflow completed/i)).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`/command-center\\?workspaceId=${demoWorkspaceId}`));
    await expectNoForbiddenVisibleCopy(page);
  });

  test("quick action unsupported shows safe error message", async ({ page, request }) => {
    await setMockApiScenario(request, "quick-action-unsupported");
    await page.goto(`/command-center?workspaceId=${demoWorkspaceId}`);

    await page.getByRole("button", { name: /Generate brief/i }).click();

    await expect(page.getByText(/backend-safe quick action is not available/i)).toBeVisible();
    await expectNoForbiddenVisibleCopy(page);
  });
});
