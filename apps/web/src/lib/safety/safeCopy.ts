import { safeTradingPhraseReplacements } from "./bannedPhrases";

export function containsUnsafeTradingPhrase(text: string): boolean {
  return safeTradingPhraseReplacements.some(([pattern]) => {
    pattern.lastIndex = 0;
    return pattern.test(text);
  });
}

export function sanitizeUnsafeCopy(label: string | null | undefined, fallback = "Not available"): string {
  const text = label?.trim() || fallback;
  return safeTradingPhraseReplacements.reduce(
    (current, [pattern, replacement]) => current.replace(pattern, replacement),
    text,
  );
}

export function assertSafeLabel(label: string): string {
  if (containsUnsafeTradingPhrase(label)) {
    throw new Error("Unsafe trading phrase found in label");
  }
  return label;
}
