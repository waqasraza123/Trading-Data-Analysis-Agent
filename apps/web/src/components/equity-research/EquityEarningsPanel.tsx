"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import {
  createEarningsCatalystContext,
  fetchEquityEarnings,
  fetchEquityFundamentals,
  lookupEquityMetadata,
} from "@/lib/api/equityData";
import { equityDataLabel, equityDataStatusTone, formatContextDate } from "@/lib/equity-data/labels";
import type { UUID } from "@/lib/api/types";
import type { EquityResearchData } from "@/lib/equity-research/types";

export function EquityEarningsPanel({ data }: { data: EquityResearchData }) {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const symbolId = selectedSymbolId(data);

  async function runEnrichment(kind: "metadata" | "fundamentals" | "earnings") {
    if (!data.workspace || !symbolId) {
      setMessage("Select a symbol before enrichment.");
      return;
    }
    setPending(true);
    const input = { workspaceId: data.workspace.id, provider: "mock_equity_data" };
    const result =
      kind === "metadata"
        ? await lookupEquityMetadata(symbolId, input)
        : kind === "fundamentals"
          ? await fetchEquityFundamentals(symbolId, input)
          : await fetchEquityEarnings(symbolId, input);
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    setMessage(`${equityDataLabel(kind)} enrichment stored ${result.data.stored_count} row(s).`);
    router.refresh();
  }

  async function createCatalyst(eventId: UUID) {
    setPending(true);
    const result = await createEarningsCatalystContext(eventId);
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    setMessage("Earnings catalyst context created.");
    router.refresh();
  }

  return (
    <Panel title="Earnings context" eyebrow="Corporate event foundation">
      {message && <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">{message}</p>}
      <div className="mb-4 flex flex-wrap gap-2">
        <button className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-semibold text-[var(--strong)] disabled:opacity-60" disabled={pending || !symbolId} type="button" onClick={() => runEnrichment("metadata")}>
          Fetch metadata
        </button>
        <button className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-semibold text-[var(--strong)] disabled:opacity-60" disabled={pending || !symbolId} type="button" onClick={() => runEnrichment("fundamentals")}>
          Fetch fundamentals
        </button>
        <button className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={pending || !symbolId} type="button" onClick={() => runEnrichment("earnings")}>
          Fetch earnings
        </button>
      </div>
      <div className="grid gap-3">
        {data.selectedEarnings.map((event) => (
          <div key={event.id} className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-[var(--strong)]">{formatContextDate(event.event_date)}</h3>
                <p className="mt-1 text-sm text-slate-500">{event.fiscal_period || "Fiscal period unavailable"} · {event.report_time || "Report time unavailable"}</p>
              </div>
              <div className="flex gap-2">
                <Badge value={equityDataLabel(event.status)} tone={equityDataStatusTone(event.status)} />
                <Badge value={equityDataLabel(event.importance)} tone={event.importance === "high" ? "warning" : "neutral"} />
              </div>
            </div>
            <button className="mt-3 rounded-md border border-[var(--line)] px-3 py-2 text-sm font-semibold text-[var(--strong)] disabled:opacity-60" disabled={pending} type="button" onClick={() => createCatalyst(event.id)}>
              Create catalyst context
            </button>
          </div>
        ))}
        {data.selectedEarnings.length === 0 && (
          <p className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4 text-sm text-slate-500">
            Earnings context unavailable.
          </p>
        )}
      </div>
    </Panel>
  );
}

function selectedSymbolId(data: EquityResearchData): UUID | null {
  return data.selectedCandidate?.symbol_id || data.selectedUniverseMembers[0]?.symbol_id || null;
}
