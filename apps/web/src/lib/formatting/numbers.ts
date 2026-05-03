export function formatPercent(value: number | string | null | undefined): string {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "Not scored";
  }
  const normalizedValue = numericValue > 1 ? numericValue / 100 : numericValue;
  return new Intl.NumberFormat("en", {
    style: "percent",
    maximumFractionDigits: 0,
  }).format(normalizedValue);
}

export function formatDecimal(value: number | string | null | undefined): string {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return "Not available";
  }
  return new Intl.NumberFormat("en", {
    maximumFractionDigits: 4,
  }).format(numericValue);
}

export function formatInteger(value: number | null | undefined): string {
  if (!Number.isFinite(value)) {
    return "0";
  }
  return new Intl.NumberFormat("en", { maximumFractionDigits: 0 }).format(value);
}
