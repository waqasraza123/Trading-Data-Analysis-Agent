import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { equityDataLabel, equityDataStatusTone } from "@/lib/equity-data/labels";
import type { EquityResearchData } from "@/lib/equity-research/types";

export function EquityDataProviderPanel({ data }: { data: EquityResearchData }) {
  return (
    <Panel title="Data providers" eyebrow="Credential reference status">
      <div className="grid gap-3">
        {data.equityDataProviders.map((provider) => {
          const refs = data.providerCredentialRefs.filter((ref) => ref.provider === provider.provider);
          return (
            <div key={provider.provider} className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-[var(--strong)]">{provider.label}</h3>
                  <p className="mt-1 text-sm text-slate-500">{provider.message}</p>
                </div>
                <Badge value={equityDataLabel(provider.status)} tone={equityDataStatusTone(provider.status)} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                <span>Universe {provider.supports_universe_import ? "available" : "missing"}</span>
                <span>Metadata {provider.supports_metadata_lookup ? "available" : "missing"}</span>
                <span>Fundamentals {provider.supports_fundamentals_snapshot ? "available" : "missing"}</span>
                <span>Earnings {provider.supports_earnings_calendar ? "available" : "missing"}</span>
              </div>
              <p className="mt-3 text-xs text-slate-500">
                {provider.requires_credential_ref
                  ? refs.length > 0
                    ? `${refs.length} credential reference${refs.length === 1 ? "" : "s"} available`
                    : "Credential reference missing"
                  : "Credential reference not required"}
              </p>
            </div>
          );
        })}
        {data.equityDataProviders.length === 0 && (
          <p className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4 text-sm text-slate-500">
            Provider capability data is unavailable.
          </p>
        )}
      </div>
    </Panel>
  );
}
