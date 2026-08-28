import { expect, test } from "@playwright/test";

test.describe("starter kit landing page", () => {
  test("presents the developer positioning and primary journeys", async ({ page }) => {
    await page.goto("/");

    await expect(
      page.getByRole("heading", {
        name: /Ship an AI trading SaaS without rebuilding the foundation/i,
      }),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: /Start from this template/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /Create a workspace/i })).toHaveAttribute(
      "href",
      "/register",
    );
    await expect(page.getByText(/No broker execution/i).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: /A vertical starter kit/i })).toBeVisible();
    await expect(page).toHaveTitle(/AI Trading SaaS Starter Kit/i);
  });

  test("keeps the core actions visible on a mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");

    await expect(page.getByRole("link", { name: "Sign in" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "Use template" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: /Create a workspace/i })).toBeVisible();
  });
});
