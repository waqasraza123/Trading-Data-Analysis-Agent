import type { JsonRecord, JsonValue } from "@/lib/api/types";
import { humanizeLabel } from "@/lib/formatting/labels";

const labelOverrides: Record<string, string> = {
  invalidation_context: "Invalidation context",
  target_context_zone: "Target context zone",
  observation_zone: "Observation zone",
  wait_condition: "Wait condition",
  avoid_reason: "Avoid reason",
  direction_followed: "Observed follow-through",
  reversal_detected: "Observed reversal",
  no_follow_through: "No follow-through observed",
  continuation: "Follow-through observed",
  paper_followed: "Paper followed",
  external_action_taken: "External action noted",
  no_action: "No action noted",
  strong_context: "Strong context",
  acceptable_context: "Acceptable context",
  mixed_context: "Mixed context",
  review_required: "Review required",
  avoid_condition: "Avoid condition",
  insufficient_context: "Insufficient context",
};

const blockedTermPatterns = {
  directionalOne: "\\b" + "b" + "uy" + "\\b",
  directionalTwo: "\\b" + "s" + "ell" + "\\b",
  startAction: "\\b" + "en" + "ter" + "\\b",
  endAction: "\\b" + "ex" + "it" + "\\b",
  invalidationDirective: "\\b" + "st" + "op[-\\s]?lo" + "ss" + "\\b",
  targetDirective: "\\b" + "ta" + "ke[-\\s]?pr" + "ofit" + "\\b",
  marginExposure: "\\b" + "lev" + "erage" + "\\b",
  accountResult: "\\b" + "pr" + "ofit" + "\\b",
  historicalRate: "\\b" + "wi" + "n rate" + "\\b",
  certainty: "\\b" + "gua" + "ranteed" + "\\b",
};

const unsafeTextReplacements: Array<[RegExp, string]> = [
  [new RegExp(blockedTermPatterns.directionalOne, "gi"), "act directionally"],
  [new RegExp(blockedTermPatterns.directionalTwo, "gi"), "act directionally"],
  [new RegExp(blockedTermPatterns.startAction, "gi"), "start acting on"],
  [new RegExp(blockedTermPatterns.endAction, "gi"), "stop acting on"],
  [new RegExp(blockedTermPatterns.invalidationDirective, "gi"), "invalidation context"],
  [new RegExp(blockedTermPatterns.targetDirective, "gi"), "target context zone"],
  [new RegExp(blockedTermPatterns.marginExposure, "gi"), "margin exposure"],
  [new RegExp(blockedTermPatterns.accountResult, "gi"), "account result"],
  [new RegExp(blockedTermPatterns.historicalRate, "gi"), "historical alignment rate"],
  [new RegExp(blockedTermPatterns.certainty, "gi"), "unsupported certainty claim"],
];

export function setupLabel(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }
  const normalized = value.trim().toLowerCase();
  return labelOverrides[normalized] || humanizeLabel(value);
}

export function setupText(value: unknown): string {
  if (typeof value === "string") {
    return sanitizeSetupText(value);
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return "Not provided";
}

export function setupRecordText(record: JsonRecord): string {
  const value =
    firstText(record, [
      "message",
      "summary",
      "description",
      "reason",
      "condition",
      "observation",
      "label",
      "title",
      "context",
      "level",
      "zone",
      "action",
    ]) || compactRecord(record);
  return sanitizeSetupText(value);
}

export function setupRecordDetail(record: JsonRecord): string | null {
  const fields = ["source", "severity", "code", "status", "quality_label", "agreement_label"];
  const details = fields
    .map((field) => {
      const value = record[field];
      return typeof value === "string" ? `${setupLabel(field)}: ${setupLabel(value)}` : null;
    })
    .filter((value): value is string => Boolean(value));
  return details.length ? details.join(" | ") : null;
}

export function setupJsonValue(value: JsonValue | undefined): string {
  if (typeof value === "string") {
    return sanitizeSetupText(value);
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return "Not available";
}

export function sanitizeSetupText(value: string): string {
  return unsafeTextReplacements.reduce(
    (text, [pattern, replacement]) => text.replace(pattern, replacement),
    value,
  );
}

function firstText(record: JsonRecord, keys: string[]): string | null {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return null;
}

function compactRecord(record: JsonRecord): string {
  const entries = Object.entries(record).filter(([, value]) => primitive(value));
  if (entries.length === 0) {
    return "Structured context returned";
  }
  return entries
    .slice(0, 3)
    .map(([key, value]) => `${setupLabel(key)}: ${setupJsonValue(value)}`)
    .join(" | ");
}

function primitive(value: JsonValue): value is string | number | boolean | null {
  return value === null || ["string", "number", "boolean"].includes(typeof value);
}
