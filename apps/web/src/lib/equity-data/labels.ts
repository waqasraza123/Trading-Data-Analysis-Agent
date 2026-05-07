import { humanizeLabel } from "@/lib/formatting/labels";

export function equityDataStatusTone(
  value: string | null | undefined,
): "neutral" | "good" | "warning" | "danger" | "info" {
  const normalized = value?.toLowerCase();
  if (normalized === "completed" || normalized === "active") {
    return "good";
  }
  if (normalized === "completed_with_warnings" || normalized === "provider_not_configured") {
    return "warning";
  }
  if (normalized === "failed") {
    return "danger";
  }
  if (normalized === "pending" || normalized === "running" || normalized === "provider_not_implemented") {
    return "info";
  }
  return "neutral";
}

export function equityDataLabel(value: string | null | undefined, fallback = "Unavailable"): string {
  const label = humanizeLabel(value);
  return label.trim() || fallback;
}

export function formatLargeNumber(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "Unavailable";
  }
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) {
    return "Unavailable";
  }
  return new Intl.NumberFormat("en", {
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(numberValue);
}

export function formatContextDate(value: string | null | undefined): string {
  if (!value) {
    return "Unavailable";
  }
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(
    new Date(value),
  );
}
