import { expect, test } from "@playwright/test";
import { setMockApiScenario } from "./fixtures/apiMocks";
import { expectNoForbiddenVisibleCopy } from "./helpers/safeText";

test.describe("onboarding smoke", () => {
  test("empty setup shows setup gaps and safe actions", async ({ page, request }) => {
    await setMockApiScenario(request, "empty-onboarding");
    await page.goto("/onboarding");

    await expect(page.getByRole("heading", { name: /First-run onboarding/i })).toBeVisible();
    await expect(page.getByText(/Setup incomplete/i)).toBeVisible();
    await expect(page.getByText(/Next step/i)).toBeVisible();
    await expect(page.getByRole("heading", { name: /Create workspace/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Complete next step/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /Run action/i }).first()).toBeVisible();
    await expectNoForbiddenVisibleCopy(page);
  });

  test("partial setup shows data, watchlist, scanner, and command-center links", async ({ page, request }) => {
    await setMockApiScenario(request, "partial-onboarding");
    await page.goto("/onboarding");

    await expect(page.getByText(/Data sources/i).first()).toBeVisible();
    await expect(page.getByText(/Watchlist/i).first()).toBeVisible();
    await expect(page.getByText(/Scan config/i).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /Data onboarding/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /^Scanner$/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /Command center/i })).toBeVisible();
    await expectNoForbiddenVisibleCopy(page);
  });

  test("ready setup shows completion panel without execution wording", async ({ page, request }) => {
    await setMockApiScenario(request, "ready-onboarding");
    await page.goto("/onboarding");

    await expect(page.getByText(/Command center ready/i).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: /Ready for deterministic analysis/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /Open command center/i })).toBeVisible();
    await expectNoForbiddenVisibleCopy(page);
  });

  test("backend unavailable renders a clean error state", async ({ page, request }) => {
    await setMockApiScenario(request, "backend-unavailable");
    await page.goto("/onboarding");

    await expect(page.getByText(/Backend unavailable/i).first()).toBeVisible();
    await expect(page.getByText(/onboarding status endpoint is unavailable/i)).toBeVisible();
    await expectNoForbiddenVisibleCopy(page);
  });
});
