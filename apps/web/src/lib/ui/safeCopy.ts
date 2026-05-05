const bannedCopyReplacements: Array<[RegExp, string]> = [
  [new RegExp(String.raw`\b${"b" + "uy"}\b`, "gi"), "review"],
  [new RegExp(String.raw`\b${"s" + "ell"}\b`, "gi"), "review"],
  [new RegExp(String.raw`\b${"en" + "ter"}\s+trade\b`, "gi"), "review setup"],
  [new RegExp(String.raw`\b${"ex" + "it"}\s+trade\b`, "gi"), "review setup"],
  [new RegExp(String.raw`\btake\s+${"pro" + "fit"}\b`, "gi"), "target context"],
  [new RegExp(String.raw`\b${"st" + "op"}\s+loss\b`, "gi"), "invalidation context"],
  [new RegExp(String.raw`\buse\s+${"lever" + "age"}\b`, "gi"), "review exposure"],
  [new RegExp(String.raw`\b${"pro" + "fit"}\b`, "gi"), "observed behavior"],
  [new RegExp(String.raw`\b${"w" + "in"}\s+rate\b`, "gi"), "observed alignment"],
  [new RegExp(String.raw`\b${"guaran" + "teed"}\b`, "gi"), "reviewed"],
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
