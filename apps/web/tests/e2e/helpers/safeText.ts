import { expect, type Page } from "@playwright/test";

export const bannedVisiblePhrases = [
  "buy now",
  "sell now",
  "enter trade",
  "exit trade",
  "take profit",
  "stop loss",
  "use leverage",
  "guaranteed",
  "guaranteed profit",
  "risk-free",
  "profit",
  "win rate",
  "ready to trade",
  "trade alert",
] as const;

export async function expectNoForbiddenVisibleCopy(page: Page) {
  const visibleText = normalizeText(await page.locator("body").innerText());
  for (const phrase of bannedVisiblePhrases) {
    expect(visibleText, `visible copy should not include "${phrase}"`).not.toContain(phrase);
  }
}

function normalizeText(value: string): string {
  return value.toLowerCase().replace(/\s+/g, " ").trim();
}
