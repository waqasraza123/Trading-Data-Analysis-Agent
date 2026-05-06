import type { Page } from "@playwright/test";

export async function mockClientOptionalEndpointFallbacks(page: Page) {
  await page.route("**/client-only-optional/**", async (route) => {
    await route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Optional endpoint unavailable" }),
    });
  });
}
