import { humanizeLabel } from "@/lib/formatting/labels";

export function qualityLabel(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }
  const labels: Record<string, string> = {
    aligned: "Aligned",
    over_confident: "Overconfidence warning",
    under_confident: "Underconfidence warning",
    review_recommended: "Review recommended",
    degraded: "Degraded",
    stable: "Stable",
    improving: "Improving",
    mixed: "Mixed",
    drift_detected: "Drift detected",
    material_drift: "Material drift",
    severe_drift: "Severe drift",
    elevated_reversal: "Elevated reversal",
    no_follow_through: "No follow-through",
    continuation: "Continuation observed",
    partial_follow_through: "Partial continuation observed",
  };
  return labels[value] || humanizeLabel(value);
}

export function formatPercent(value: number | string | null | undefined): string {
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) {
    return "Not available";
  }
  return `${Math.round(parsed * 100)}%`;
}

export function formatNumber(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return "0";
  }
  return new Intl.NumberFormat("en-US").format(value);
}

export function qualityTone(value: string | null | undefined): "neutral" | "good" | "warning" | "danger" | "info" {
  const normalized = value?.toLowerCase() || "";
  if (normalized.includes("strong") || normalized.includes("stable") || normalized.includes("aligned") || normalized.includes("improving")) {
    return "good";
  }
  if (normalized.includes("review") || normalized.includes("mixed") || normalized.includes("under")) {
    return "info";
  }
  if (normalized.includes("degraded") || normalized.includes("drift") || normalized.includes("over") || normalized.includes("elevated")) {
    return "warning";
  }
  if (normalized.includes("severe") || normalized.includes("failed")) {
    return "danger";
  }
  return "neutral";
}

export function noDataMessage(): string {
  return "Run diagnostics first or broaden the filters to include stored deterministic outcomes.";
}
