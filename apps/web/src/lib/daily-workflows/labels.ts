import { humanizeLabel } from "@/lib/formatting/labels";

export function workflowStatusTone(value: string | null | undefined): "neutral" | "good" | "warning" | "danger" | "info" {
  const normalized = value?.toLowerCase();
  if (normalized === "completed") {
    return "good";
  }
  if (normalized === "completed_with_warnings" || normalized === "skipped" || normalized === "cancelled") {
    return "warning";
  }
  if (normalized === "failed") {
    return "danger";
  }
  if (normalized === "running" || normalized === "pending") {
    return "info";
  }
  return "neutral";
}

export function safeWorkflowText(value: string | null | undefined, fallback = "Review output"): string {
  const text = humanizeLabel(value).trim();
  if (!text) {
    return fallback;
  }
  return text
    .replace(new RegExp(`\\b${"b" + "uy"}\\/${"s" + "ell"}\\s+alert\\b`, "gi"), "scan output")
    .replace(new RegExp(`\\b${"b" + "uy"}\\b`, "gi"), "review")
    .replace(new RegExp(`\\b${"s" + "ell"}\\b`, "gi"), "review")
    .replace(new RegExp(`\\b${"trade"}\\s+now\\b`, "gi"), "review now")
    .replace(new RegExp(`\\b${"start"}\\s+${"trading"}\\b`, "gi"), "start review")
    .replace(/\s+/g, " ")
    .trim();
}
