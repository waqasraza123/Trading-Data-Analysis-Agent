import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { equityDataLabel, equityDataStatusTone, formatContextDate } from "@/lib/equity-data/labels";
import type { EquityResearchData } from "@/lib/equity-research/types";

export function EquityProviderRequestHistory({ data }: { data: EquityResearchData }) {
  return (
    <Panel title="Provider requests" eyebrow="Recent enrichment runs">
      <div className="grid gap-3">
        {data.providerRequests.map((request) => (
          <div key={request.id} className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-[var(--strong)]">{equityDataLabel(request.request_type)}</h3>
                <p className="mt-1 text-sm text-slate-500">{request.provider} · {formatContextDate(request.created_at)}</p>
              </div>
              <Badge value={equityDataLabel(request.status)} tone={equityDataStatusTone(request.status)} />
            </div>
            <p className="mt-3 text-xs text-slate-500">
              Received {request.received_count} · Stored {request.stored_count} · Skipped {request.skipped_count}
            </p>
          </div>
        ))}
        {data.providerRequests.length === 0 && (
          <p className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4 text-sm text-slate-500">
            No equity data provider requests yet.
          </p>
        )}
      </div>
    </Panel>
  );
}
