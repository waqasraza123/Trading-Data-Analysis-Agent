const bannedCopyReplacements: Array<[RegExp, string]> = [
  [/\bbuy\b/gi, "review"],
  [/\bsell\b/gi, "review"],
  [/\benter\s+trade\b/gi, "review setup"],
  [/\bexit\s+trade\b/gi, "review setup"],
  [/\btake\s+profit\b/gi, "target context"],
  [/\bstop\s+loss\b/gi, "invalidation context"],
  [/\buse\s+leverage\b/gi, "review exposure"],
  [/\bprofit\b/gi, "observed behavior"],
  [/\bwin\s+rate\b/gi, "observed alignment"],
  [/\bguaranteed\b/gi, "reviewed"],
];

export function safeCopy(value: string | null | undefined, fallback = "Not available"): string {
  const text = value?.trim() || fallback;
  return bannedCopyReplacements.reduce((current, [pattern, replacement]) => current.replace(pattern, replacement), text);
}

export function hasUnsafeCopy(value: string): boolean {
  return bannedCopyReplacements.some(([pattern]) => {
    pattern.lastIndex = 0;
    return pattern.test(value);
  });
}
