import { humanizeLabel } from "@/lib/formatting/labels";

const safeLabelOverrides: Record<string, string> = {
  buy: "Review",
  sell: "Review",
  enter_trade: "Review setup",
  exit_trade: "Review setup",
  take_profit: "Target context",
  stop_loss: "Invalidation context",
  use_leverage: "Exposure note",
  profit: "Observed behavior",
  win_rate: "Observed alignment",
  guaranteed: "Reviewed",
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
  return safeLabelOverrides[normalized] || humanizeLabel(value);
}

export function workspaceLabel(value: string | null | undefined): string {
  return value ? `Workspace ${value}` : "Workspace not selected";
}

export function lastUpdatedLabel(value: string): string {
  return `Updated ${value}`;
}
