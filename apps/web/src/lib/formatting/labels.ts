const labelOverrides: Record<string, string> = {
  bullish: "Bullish bias",
  bearish: "Bearish bias",
  neutral: "Neutral",
  no_signal: "No directional signal",
  no_directional_signal: "No directional signal",
  review_recommended: "Review recommended",
  stale: "Data stale",
  degraded: "Degraded",
  fresh: "Fresh",
  strong: "Strong",
  acceptable: "Acceptable",
  weak: "Weak",
  insufficient_data: "Insufficient future data",
  continuation: "Follow-through observed",
  partial_follow_through: "Partial follow-through observed",
  reversal: "Reversal observed",
  no_follow_through: "No follow-through observed",
};

export function humanizeLabel(value: string | null | undefined): string {
  if (!value) {
    return "Not available";
  }
  const normalizedValue = value.trim().toLowerCase();
  return (
    labelOverrides[normalizedValue] ||
    normalizedValue
      .split(/[_\s-]+/)
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ")
  );
}

export function shortIdentifier(value: string | null | undefined): string {
  if (!value) {
    return "Unknown";
  }
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value;
}
