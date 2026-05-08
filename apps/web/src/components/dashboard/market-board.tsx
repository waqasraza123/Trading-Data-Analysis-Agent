import Link from "next/link";
import { EmptyState } from "@/components/empty-states/empty-state";
import { Panel } from "@/components/layout/panel";
import { Badge, toneForBias, toneForQuality } from "@/components/status/badge";
import type { DashboardData } from "@/lib/api/dashboard";
import type { MarketMemorySnapshot, SymbolRead, WatchlistItem } from "@/lib/api/types";
import { formatRelativeTime } from "@/lib/formatting/dates";
import { humanizeLabel, shortIdentifier } from "@/lib/formatting/labels";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle } from "@/lib/ui/motion";

type MarketBoardRow = {
  id: string;
  symbol: SymbolRead | null;
  symbolId: string;
  timeframe: string;
  memory: MarketMemorySnapshot | null;
  watchlistItem: WatchlistItem | null;
};

export function MarketBoard({ data }: { data: DashboardData }) {
  const rows = buildRows(data);

  return (
    <Panel title="Market Board" eyebrow="Watchlist state">
      {rows.length === 0 ? (
        <EmptyState
          title="No symbol state available"
          message="Add watchlist items or refresh market memory snapshots to populate this board."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
          {rows.map((row, index) => (
            <AnimatedListItem
              as="article"
              key={row.id}
              className={`${motionCardClass} muted-surface rounded-lg p-4`}
              preset="scale-subtle"
              style={motionRevealDensityStyle(index, "compact")}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <Link
                    className="text-lg font-semibold text-[var(--strong)] hover:text-[var(--accent)]"
                    href={`/symbols/${row.symbolId}${data.workspace ? `?workspaceId=${data.workspace.id}` : ""}`}
                  >
                    {row.symbol?.symbol || shortIdentifier(row.symbolId)}
                  </Link>
                  <p className="mt-1 text-sm text-slate-500">{row.symbol?.display_name || "Symbol metadata unavailable"}</p>
                </div>
                <Badge value={row.timeframe} tone="info" />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Badge value={row.memory?.freshness_label || "No freshness state"} tone={toneForQuality(row.memory?.freshness_label)} />
                <Badge value={row.memory?.data_quality_label || "No quality state"} tone={toneForQuality(row.memory?.data_quality_label)} />
                <Badge value={row.memory?.latest_signal_bias || "No directional signal"} tone={toneForBias(row.memory?.latest_signal_bias)} />
                <Badge value={row.memory?.latest_signal_confidence_label || "Not scored"} tone={toneForQuality(row.memory?.latest_signal_confidence_label)} />
              </div>
              <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                <Detail label="Pattern" value={humanizeLabel(row.memory?.latest_signal_pattern_type)} />
                <Detail label="Regime" value={humanizeLabel(row.memory?.market_regime_label)} />
                <Detail label="Session" value={humanizeLabel(row.memory?.market_session_label)} />
                <Detail label="Latest final candle" value={formatRelativeTime(row.memory?.latest_final_candle_time)} />
              </dl>
              {row.memory?.latest_signal_id && (
                <Link
                  className="mt-4 inline-flex rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium hover:bg-white dark:hover:bg-slate-900"
                  href={`/dashboard?workspaceId=${row.memory.workspace_id}&signalId=${row.memory.latest_signal_id}`}
                >
                  Focus signal
                </Link>
              )}
              {row.memory?.warnings_json?.length ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {row.memory.warnings_json.slice(0, 3).map((warning, index) => (
                    <Badge key={`${row.id}-warning-${index}`} value={warningLabel(warning)} tone="warning" />
                  ))}
                </div>
              ) : null}
            </AnimatedListItem>
          ))}
        </div>
      )}
    </Panel>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-[var(--strong)]">{value}</dd>
    </div>
  );
}

function buildRows(data: DashboardData): MarketBoardRow[] {
  const symbolMap = new Map(data.symbols.map((symbol) => [symbol.id, symbol]));
  const rows = new Map<string, MarketBoardRow>();
  for (const snapshot of data.memorySnapshots) {
    rows.set(`${snapshot.symbol_id}:${snapshot.timeframe}`, {
      id: `${snapshot.symbol_id}:${snapshot.timeframe}`,
      symbol: symbolMap.get(snapshot.symbol_id) || null,
      symbolId: snapshot.symbol_id,
      timeframe: snapshot.timeframe,
      memory: snapshot,
      watchlistItem: null,
    });
  }
  for (const watchlist of data.watchlists) {
    for (const item of watchlist.items) {
      const key = `${item.symbol_id}:${item.timeframe}`;
      const existing = rows.get(key);
      rows.set(key, {
        id: key,
        symbol: symbolMap.get(item.symbol_id) || existing?.symbol || null,
        symbolId: item.symbol_id,
        timeframe: item.timeframe,
        memory: existing?.memory || null,
        watchlistItem: item,
      });
    }
  }
  return Array.from(rows.values()).sort((left, right) => {
    const leftLabel = left.symbol?.symbol || left.symbolId;
    const rightLabel = right.symbol?.symbol || right.symbolId;
    return `${leftLabel}:${left.timeframe}`.localeCompare(`${rightLabel}:${right.timeframe}`);
  });
}

function warningLabel(value: Record<string, unknown>): string {
  const code = value.code;
  const message = value.message;
  if (typeof message === "string") {
    return message;
  }
  if (typeof code === "string") {
    return code;
  }
  return "Review recommended";
}
