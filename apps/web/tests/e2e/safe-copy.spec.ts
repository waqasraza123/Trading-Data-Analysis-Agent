import { test } from "@playwright/test";
import { setMockApiScenario } from "./fixtures/apiMocks";
import { demoWorkspaceId } from "./fixtures/workspaceFixtures";
import { expectNoForbiddenVisibleCopy } from "./helpers/safeText";

const safeCopyRoutes = [
  "/onboarding",
  "/command-center",
  "/triage",
] as const;

test.describe("visible safe-copy smoke", () => {
  for (const route of safeCopyRoutes) {
    test(`${route} has no forbidden trading-advice copy`, async ({ page, request }) => {
      await setMockApiScenario(request, "safe-copy");
      await page.goto(`${route}?workspaceId=${demoWorkspaceId}`);
      await expectNoForbiddenVisibleCopy(page);
    });
  }
});
