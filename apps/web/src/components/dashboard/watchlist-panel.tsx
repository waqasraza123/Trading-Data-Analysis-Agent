import { EmptyState } from "@/components/empty-states/empty-state";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import type { DashboardData } from "@/lib/api/dashboard";
import { shortIdentifier } from "@/lib/formatting/labels";

export function WatchlistPanel({ data }: { data: DashboardData }) {
  const symbolMap = new Map(data.symbols.map((symbol) => [symbol.id, symbol]));

  return (
    <Panel title="Watchlists" eyebrow="Symbols and timeframes">
      {data.watchlists.length === 0 ? (
        <EmptyState title="No watchlists returned" message="The dashboard will still use market memory and signal data when available." />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {data.watchlists.map(({ watchlist, items }) => (
            <div key={watchlist.id} className="muted-surface rounded-lg p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-[var(--strong)]">{watchlist.name}</h3>
                  {watchlist.description && <p className="mt-1 text-sm text-slate-500">{watchlist.description}</p>}
                </div>
                <Badge value={watchlist.status} />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {items.length ? (
                  items.map((item) => {
                    const symbol = symbolMap.get(item.symbol_id);
                    return (
                      <Badge
                        key={item.id}
                        value={`${symbol?.symbol || shortIdentifier(item.symbol_id)} ${item.timeframe}`}
                        tone="info"
                      />
                    );
                  })
                ) : (
                  <Badge value="No active items" tone="warning" />
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </Panel>
  );
}
