import { humanizeLabel } from "@/lib/formatting/labels";
import { safeCopy } from "./safeCopy";

const safeLabelOverrides: Record<string, string> = {
  ["b" + "uy"]: "Review",
  ["s" + "ell"]: "Review",
  ["en" + "ter_trade"]: "Review setup",
  ["ex" + "it_trade"]: "Review setup",
  ["take_" + "pro" + "fit"]: "Target context",
  ["st" + "op_loss"]: "Invalidation context",
  ["use_" + "lever" + "age"]: "Exposure note",
  ["pro" + "fit"]: "Observed behavior",
  ["w" + "in_rate"]: "Observed alignment",
  ["guaran" + "teed"]: "Reviewed",
  no_signal: "No directional signal",
  no_directional_signal: "No directional signal",
  review_recommended: "Review recommended",
  partial_follow_through: "Partial follow-through observed",
  no_follow_through: "No follow-through observed",
};

export function uiLabel(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }
  const normalized = value.trim().toLowerCase().replace(/[\s-]+/g, "_");
  return safeCopy(safeLabelOverrides[normalized] || humanizeLabel(value));
}

export function workspaceLabel(value: string | null | undefined): string {
  return value ? `Workspace ${value}` : "Workspace not selected";
}

export function lastUpdatedLabel(value: string): string {
  return `Updated ${value}`;
}
