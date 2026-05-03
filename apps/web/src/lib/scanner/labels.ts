import type { SymbolRead, UUID } from "@/lib/api/types";
import { humanizeLabel, shortIdentifier } from "@/lib/formatting/labels";
import type { ScannerDataSource } from "@/lib/scanner/types";

export const scannerTimeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"] as const;

export function symbolLabel(symbols: SymbolRead[], symbolId: UUID | null | undefined): string {
  if (!symbolId) {
    return "Any symbol";
  }
  const symbol = symbols.find((candidate) => candidate.id === symbolId);
  return symbol ? `${symbol.symbol} · ${symbol.display_name}` : shortIdentifier(symbolId);
}

export function compactSymbolLabel(symbols: SymbolRead[], symbolId: UUID | null | undefined): string {
  if (!symbolId) {
    return "Any symbol";
  }
  return symbols.find((candidate) => candidate.id === symbolId)?.symbol || shortIdentifier(symbolId);
}

export function sourceLabel(sources: ScannerDataSource[], sourceId: UUID | null | undefined): string {
  if (!sourceId) {
    return "Any active source";
  }
  const source = sources.find((candidate) => candidate.id === sourceId);
  return source ? `${source.name} · ${source.provider}` : shortIdentifier(sourceId);
}

export function scanTargetLabel(config: {
  scan_mode: string;
  watchlist_id: UUID | null;
  symbol_id: UUID | null;
  timeframe: string | null;
}, watchlistName: string | null, symbols: SymbolRead[]): string {
  if (config.scan_mode === "watchlist") {
    return watchlistName || shortIdentifier(config.watchlist_id || "");
  }
  return `${compactSymbolLabel(symbols, config.symbol_id)} ${config.timeframe || ""}`.trim();
}

export function statusTone(value: string | null | undefined): "neutral" | "good" | "warning" | "danger" | "info" {
  const normalized = value?.toLowerCase();
  if (normalized === "active" || normalized === "completed") {
    return "good";
  }
  if (normalized === "paused" || normalized === "skipped" || normalized === "completed_with_warnings") {
    return "warning";
  }
  if (normalized === "failed" || normalized === "archived") {
    return "danger";
  }
  if (normalized === "running" || normalized === "pending") {
    return "info";
  }
  return "neutral";
}

export function safeScannerText(value: string | null | undefined, fallback = "Review result"): string {
  const text = humanizeLabel(value).trim();
  if (!text) {
    return fallback;
  }
  return text
    .replace(/\btrade scan\b/gi, "watchlist scan")
    .replace(/\bbuy\/sell alert\b/gi, "scan result")
    .replace(/\bbuy\b/gi, "review")
    .replace(/\bsell\b/gi, "review")
    .replace(/\bentry\b/gi, "observation")
    .replace(/\bexit\b/gi, "observation")
    .replace(/\bprofit\b/gi, "observed behavior")
    .replace(/\bguaranteed\b/gi, "reviewed")
    .replace(/\s+/g, " ")
    .trim();
}
