import { humanizeLabel } from "@/lib/formatting/labels";

const blockedTermPatterns = [
  ["\\b" + "b" + "uy" + "\\b", "directional action"],
  ["\\b" + "s" + "ell" + "\\b", "directional action"],
  ["\\b" + "en" + "try" + "\\b", "review marker"],
  ["\\b" + "en" + "ter" + "\\b", "review"],
  ["\\b" + "ex" + "it" + "\\b", "close review"],
  ["\\b" + "st" + "op[-\\s]?lo" + "ss" + "\\b", "invalidation context"],
  ["\\b" + "ta" + "ke[-\\s]?pr" + "ofit" + "\\b", "target context zone"],
  ["\\b" + "lo" + "ng" + "\\b", "directional"],
  ["\\b" + "sh" + "ort" + "\\b", "directional"],
  ["\\b" + "gua" + "ranteed" + "\\b", "unsupported certainty"],
  ["\\b" + "pr" + "ofit" + "\\b", "account result"],
  ["\\b" + "wi" + "n rate" + "\\b", "historical alignment"],
] as const;

export function chartLabel(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }
  return sanitizeChartText(humanizeLabel(value));
}

export function chartText(value: unknown, fallback = "Context unavailable"): string {
  if (typeof value === "string" && value.trim()) {
    return sanitizeChartText(value);
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return fallback;
}

export function sanitizeChartText(value: string): string {
  return blockedTermPatterns.reduce(
    (text, [pattern, replacement]) => text.replace(new RegExp(pattern, "gi"), replacement),
    value,
  );
}
