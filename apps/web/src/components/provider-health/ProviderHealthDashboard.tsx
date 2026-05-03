"use client";

import { useState } from "react";
import type { ApiError, SymbolRead, UUID, Workspace } from "@/lib/api/types";
import {
  getProviderHealthSummary,
  prepareProviderHealthGapRecovery,
  refreshProviderHealthWorkspace,
} from "@/lib/api/providerHealth";
import type { DataSource } from "@/lib/data-onboarding/types";
import type {
  ProviderHealthPrepareGapRecoveryResponse,
  ProviderHealthSnapshot,
  ProviderHealthSummary,
} from "@/lib/provider-health/types";
import { CandleFreshnessMatrix } from "./CandleFreshnessMatrix";
import { GapRecoveryPanel } from "./GapRecoveryPanel";
import { ProviderFailurePanel } from "./ProviderFailurePanel";
import { ProviderHealthEmptyState } from "./ProviderHealthEmptyState";
import { ProviderHealthErrorState } from "./ProviderHealthErrorState";
import { ProviderHealthHeader } from "./ProviderHealthHeader";
import { ProviderHealthSummaryCards } from "./ProviderHealthSummaryCards";
import { ProviderHealthTable } from "./ProviderHealthTable";
import { ProviderPollingRequestPanel } from "./ProviderPollingRequestPanel";

type ProviderHealthDashboardProps = {
  workspace: Workspace | null;
  symbols: SymbolRead[];
  dataSources: DataSource[];
  initialSnapshots: ProviderHealthSnapshot[];
  initialSummary: ProviderHealthSummary | null;
  initialError: ApiError | null;
};

export function ProviderHealthDashboard({
  workspace,
  symbols,
  dataSources,
  initialSnapshots,
  initialSummary,
  initialError,
}: ProviderHealthDashboardProps) {
  const [snapshots, setSnapshots] = useState(initialSnapshots);
  const [summary, setSummary] = useState(initialSummary);
  const [error, setError] = useState<ApiError | null>(initialError);
  const [loading, setLoading] = useState(false);
  const [preparingSnapshotId, setPreparingSnapshotId] = useState<UUID | null>(null);
  const [recovery, setRecovery] = useState<ProviderHealthPrepareGapRecoveryResponse | null>(null);

  async function refreshHealth() {
    if (!workspace) {
      return;
    }
    setLoading(true);
    setError(null);
    const result = await refreshProviderHealthWorkspace(workspace.id);
    if (result.ok) {
      setSnapshots(result.data.snapshots);
      const summaryResult = await getProviderHealthSummary(workspace.id);
      setSummary(summaryResult.ok ? summaryResult.data : null);
      if (!summaryResult.ok && !summaryResult.error.missing) {
        setError(summaryResult.error);
      }
    } else {
      setError(result.error);
    }
    setLoading(false);
  }

  async function prepareRecovery(snapshot: ProviderHealthSnapshot) {
    setPreparingSnapshotId(snapshot.id);
    setError(null);
    const result = await prepareProviderHealthGapRecovery(snapshot.id, false);
    if (result.ok) {
      setRecovery(result.data);
      setSnapshots((current) =>
        current.map((candidate) =>
          candidate.id === result.data.snapshot.id ? result.data.snapshot : candidate,
        ),
      );
    } else {
      setError(result.error);
    }
    setPreparingSnapshotId(null);
  }

  return (
    <section className="surface rounded-lg p-5">
      <div className="space-y-5">
        <ProviderHealthHeader workspace={workspace} loading={loading} onRefresh={refreshHealth} />
        {error && <ProviderHealthErrorState error={error} />}
        {!workspace ? (
          <ProviderHealthEmptyState
            title="No workspace available"
            message="Provider health requires a workspace."
          />
        ) : (
          <>
            <ProviderHealthSummaryCards summary={summary} />
            <ProviderHealthTable
              snapshots={snapshots}
              symbols={symbols}
              dataSources={dataSources}
              preparingSnapshotId={preparingSnapshotId}
              onPrepareRecovery={prepareRecovery}
            />
            <div className="grid gap-4 xl:grid-cols-2">
              <div>
                <h3 className="mb-3 text-sm font-semibold text-[var(--strong)]">Candle freshness</h3>
                <CandleFreshnessMatrix snapshots={snapshots} />
              </div>
              <div>
                <h3 className="mb-3 text-sm font-semibold text-[var(--strong)]">Recent failures</h3>
                <ProviderFailurePanel snapshots={snapshots} />
              </div>
              <div>
                <h3 className="mb-3 text-sm font-semibold text-[var(--strong)]">Gap recovery</h3>
                <GapRecoveryPanel recovery={recovery} />
              </div>
              <div>
                <h3 className="mb-3 text-sm font-semibold text-[var(--strong)]">Provider polling requests</h3>
                <ProviderPollingRequestPanel recovery={recovery} />
              </div>
            </div>
          </>
        )}
      </div>
    </section>
  );
}
