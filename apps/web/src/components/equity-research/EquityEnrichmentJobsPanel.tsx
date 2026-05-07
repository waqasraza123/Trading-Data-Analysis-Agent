"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Panel } from "@/components/layout/panel";
import {
  queueEquityEarningsEnrichment,
  queueEquityEarningsToCatalysts,
  queueEquityFundamentalsEnrichment,
  queueEquityMetadataEnrichment,
} from "@/lib/api/equityData";
import type { EquityDataOperationInput } from "@/lib/equity-data/types";
import type { EquityResearchData } from "@/lib/equity-research/types";

type EnrichmentKind = "metadata" | "fundamentals" | "earnings" | "catalysts";

export function EquityEnrichmentJobsPanel({ data }: { data: EquityResearchData }) {
  const router = useRouter();
  const readyProvider = data.equityDataProviders.find((provider) => provider.provider === "mock_equity_data") || data.equityDataProviders[0];
  const [provider, setProvider] = useState(readyProvider?.provider || "mock_equity_data");
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState<EnrichmentKind | null>(null);
  const disabled = !data.workspace || !data.selectedUniverse;

  async function queue(kind: EnrichmentKind) {
    if (!data.workspace || !data.selectedUniverse) {
      setMessage("Workspace and universe scope are required.");
      return;
    }
    setPending(kind);
    const input: EquityDataOperationInput = {
      workspaceId: data.workspace.id,
      universeId: data.selectedUniverse.id,
      provider,
      runMode: "queued",
      limit: 250,
    };
    const result =
      kind === "metadata"
        ? await queueEquityMetadataEnrichment(input)
        : kind === "fundamentals"
          ? await queueEquityFundamentalsEnrichment(input)
          : kind === "earnings"
            ? await queueEquityEarningsEnrichment(input)
            : await queueEquityEarningsToCatalysts({
                workspaceId: data.workspace.id,
                universeId: data.selectedUniverse.id,
                runMode: "queued",
                limit: 250,
              });
    setPending(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    setMessage(`Queued ${label(kind)} operation ${result.data.id.slice(0, 8)}.`);
    router.refresh();
  }

  return (
    <Panel title="Enrichment operations" eyebrow="Queued research context updates">
      {message && <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">{message}</p>}
      <div className="grid gap-4">
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          Provider
          <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" value={provider} onChange={(event) => setProvider(event.target.value)}>
            {data.equityDataProviders.map((item) => (
              <option key={item.provider} value={item.provider}>
                {item.label}
              </option>
            ))}
            {data.equityDataProviders.length === 0 && <option value="mock_equity_data">Mock equity data</option>}
          </select>
        </label>
        <p className="text-xs text-slate-500">
          Scope is the selected research universe. External providers remain disabled until credential references and external requests are ready.
        </p>
        <div className="grid gap-2 sm:grid-cols-2">
          <Action label="Queue metadata" disabled={disabled || pending !== null} pending={pending === "metadata"} onClick={() => queue("metadata")} />
          <Action label="Queue fundamentals" disabled={disabled || pending !== null} pending={pending === "fundamentals"} onClick={() => queue("fundamentals")} />
          <Action label="Queue earnings" disabled={disabled || pending !== null} pending={pending === "earnings"} onClick={() => queue("earnings")} />
          <Action label="Queue earnings catalysts" disabled={disabled || pending !== null} pending={pending === "catalysts"} onClick={() => queue("catalysts")} />
        </div>
      </div>
    </Panel>
  );
}

function Action({
  label,
  disabled,
  pending,
  onClick,
}: {
  label: string;
  disabled: boolean;
  pending: boolean;
  onClick: () => void;
}) {
  return (
    <button className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-semibold text-[var(--strong)] disabled:opacity-60" disabled={disabled} type="button" onClick={onClick}>
      {pending ? "Queueing" : label}
    </button>
  );
}

function label(kind: EnrichmentKind): string {
  if (kind === "metadata") {
    return "metadata";
  }
  if (kind === "fundamentals") {
    return "fundamentals";
  }
  if (kind === "earnings") {
    return "earnings";
  }
  return "earnings catalyst";
}
