"use client";

import { useEffect, useMemo, useState } from "react";
import { countCandles, getCandleQuality, getLatestCandle } from "@/lib/api/candles";
import { createDataSource, listDataSources } from "@/lib/api/dataSources";
import { runCandleRangeQuality } from "@/lib/api/dataQuality";
import {
  createCandleGapRecoveryPlan,
  listCandleGapRecoveryItems,
  prepareProviderPollingRequests,
} from "@/lib/api/gapRecovery";
import { listLiveSubscriptions } from "@/lib/api/liveFeeds";
import { listMarketMemorySnapshots } from "@/lib/api/market";
import { listProviderPollingRequests } from "@/lib/api/providerPolling";
import type { ApiError, MarketMemorySnapshot, SymbolRead, UUID } from "@/lib/api/types";
import { composeDataHealth } from "@/lib/data-onboarding/composeDataHealth";
import type {
  DataHealthRow,
  DataSource,
  GapDetectionRow,
  OnboardingInitialData,
  OnboardingSelection,
  OnboardingStepKey,
  RecoveryPreparationRow,
} from "@/lib/data-onboarding/types";
import { onboardingTimeframes } from "@/lib/data-onboarding/types";
import { DataOnboardingHeader } from "./DataOnboardingHeader";
import { DataSourceStep } from "./DataSourceStep";
import { FreshnessCheckStep } from "./FreshnessCheckStep";
import { GapDetectionStep } from "./GapDetectionStep";
import { OnboardingEmptyState } from "./OnboardingEmptyState";
import { OnboardingErrorState } from "./OnboardingErrorState";
import { OnboardingSummary } from "./OnboardingSummary";
import { RecoveryPlanStep } from "./RecoveryPlanStep";
import { SymbolSelectionStep } from "./SymbolSelectionStep";
import { TimeframeSelectionStep } from "./TimeframeSelectionStep";

type OnboardingWorkflowProps = {
  initialData: OnboardingInitialData;
};

type LoadState = "idle" | "loading" | "success" | "error";

const storageKey = "trading-data-onboarding-selection";
const healthLookbackCandles = 120;
const timeframeDurationsMs: Record<string, number> = {
  "1m": 60_000,
  "5m": 300_000,
  "15m": 900_000,
  "30m": 1_800_000,
  "1h": 3_600_000,
  "4h": 14_400_000,
  "1d": 86_400_000,
};

const steps: Array<{ key: OnboardingStepKey; label: string }> = [
  { key: "data_source", label: "Data source" },
  { key: "symbols", label: "Symbols" },
  { key: "timeframes", label: "Timeframes" },
  { key: "freshness", label: "Freshness" },
  { key: "gaps", label: "Gaps" },
  { key: "recovery", label: "Recovery" },
  { key: "summary", label: "Summary" },
];

export function OnboardingWorkflow({ initialData }: OnboardingWorkflowProps) {
  const [activeStep, setActiveStep] = useState<OnboardingStepKey>("data_source");
  const [selection, setSelection] = useState<OnboardingSelection>(() =>
    initialSelection(initialData),
  );
  const [dataSources, setDataSources] = useState<DataSource[]>(initialData.dataSources);
  const [memorySnapshots, setMemorySnapshots] = useState<MarketMemorySnapshot[]>(
    initialData.memorySnapshots,
  );
  const [sourceLoadState, setSourceLoadState] = useState<LoadState>("idle");
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [freshnessState, setFreshnessState] = useState<LoadState>("idle");
  const [gapState, setGapState] = useState<LoadState>("idle");
  const [recoveryState, setRecoveryState] = useState<LoadState>("idle");
  const [healthRows, setHealthRows] = useState<DataHealthRow[]>([]);
  const [gapRows, setGapRows] = useState<GapDetectionRow[]>([]);
  const [recoveryRows, setRecoveryRows] = useState<RecoveryPreparationRow[]>([]);

  const selectedWorkspace =
    initialData.workspaces.find((workspace) => workspace.id === selection.workspaceId) ||
    initialData.workspace;
  const selectedSource = dataSources.find((source) => source.id === selection.sourceId) || null;
  const selectedSymbols = initialData.symbols.filter((symbol) =>
    selection.symbolIds.includes(symbol.id),
  );
  const validation = validateSelection(selection);

  useEffect(() => {
    const restored = readStoredSelection(initialData);
    if (restored) {
      setSelection(restored);
    }
  }, [initialData]);

  useEffect(() => {
    persistSelection(selection);
  }, [selection]);

  useEffect(() => {
    if (!selection.workspaceId) {
      setDataSources([]);
      setMemorySnapshots([]);
      return;
    }
    let cancelled = false;
    setSourceLoadState("loading");
    Promise.all([
      listDataSources(selection.workspaceId),
      listMarketMemorySnapshots(selection.workspaceId),
    ]).then(([sourcesResult, memoryResult]) => {
      if (cancelled) {
        return;
      }
      if (sourcesResult.ok) {
        setDataSources(sourcesResult.data);
        setSelection((current) => ({
          ...current,
          sourceId:
            current.sourceId && sourcesResult.data.some((source) => source.id === current.sourceId)
              ? current.sourceId
              : sourcesResult.data[0]?.id || null,
        }));
      }
      if (memoryResult.ok) {
        setMemorySnapshots(memoryResult.data);
      }
      setSourceLoadState(sourcesResult.ok && memoryResult.ok ? "success" : "error");
    });
    return () => {
      cancelled = true;
    };
  }, [selection.workspaceId]);

  const stepIndex = steps.findIndex((step) => step.key === activeStep);
  const canRunFreshness = validation.length === 0;
  const safeNextSteps = useMemo(() => nextBackendActions(healthRows, gapRows, recoveryRows), [
    healthRows,
    gapRows,
    recoveryRows,
  ]);

  async function handleCreateSource(payload: {
    name: string;
    sourceType: string;
    provider: string;
  }) {
    if (!selection.workspaceId) {
      setWorkflowError("Select a workspace before creating a data source.");
      return;
    }
    setWorkflowError(null);
    const result = await createDataSource({
      workspace_id: selection.workspaceId,
      name: payload.name,
      source_type: payload.sourceType,
      provider: payload.provider,
      status: "active",
      config_json: {},
    });
    if (!result.ok) {
      setWorkflowError(result.error.message);
      return;
    }
    setDataSources((current) => [result.data, ...current]);
    setSelection((current) => ({ ...current, sourceId: result.data.id }));
  }

  async function handleRunFreshnessCheck() {
    if (!selection.workspaceId || !selection.sourceId || selectedSymbols.length === 0) {
      return;
    }
    setWorkflowError(null);
    setFreshnessState("loading");
    setGapRows([]);
    setRecoveryRows([]);
    const rows = await Promise.all(
      selectedSymbols.flatMap((symbol) =>
        selection.timeframes.map((timeframe) =>
          loadHealthRow({
            workspaceId: selection.workspaceId as UUID,
            sourceId: selection.sourceId,
            symbol,
            timeframe,
            memorySnapshots,
          }),
        ),
      ),
    );
    setHealthRows(rows);
    setFreshnessState("success");
    setActiveStep("freshness");
  }

  async function handleDetectGaps() {
    if (healthRows.length === 0) {
      return;
    }
    setWorkflowError(null);
    setGapState("loading");
    const rows = await Promise.all(
      healthRows.map(async (health): Promise<GapDetectionRow> => {
        const planResult = await createCandleGapRecoveryPlan({
          workspace_id: health.target.workspaceId,
          symbol_id: health.target.symbol.id,
          source_id: health.target.sourceId,
          timeframe: health.target.timeframe,
          start_time: health.target.startTime,
          end_time: health.target.endTime,
        });
        if (!planResult.ok) {
          return {
            health,
            plan: null,
            items: [],
            errors: [planResult.error],
          };
        }
        const itemsResult = await listCandleGapRecoveryItems(planResult.data.id);
        return {
          health,
          plan: planResult.data,
          items: itemsResult.ok ? itemsResult.data : [],
          errors: itemsResult.ok ? [] : [itemsResult.error],
        };
      }),
    );
    setGapRows(rows);
    setGapState("success");
    setActiveStep("gaps");
  }

  async function handlePrepareRecovery() {
    const preparedPlans = gapRows.filter((row) => row.plan && row.items.length > 0);
    if (preparedPlans.length === 0) {
      return;
    }
    setWorkflowError(null);
    setRecoveryState("loading");
    const rows = await Promise.all(
      preparedPlans.map(async (gap): Promise<RecoveryPreparationRow> => {
        if (!gap.plan) {
          return { gap, preparation: null, requests: [], errors: [] };
        }
        const result = await prepareProviderPollingRequests(gap.plan.id, false);
        if (!result.ok) {
          return { gap, preparation: null, requests: [], errors: [result.error] };
        }
        return { gap, preparation: result.data, requests: result.data.requests, errors: [] };
      }),
    );
    setRecoveryRows(rows);
    setRecoveryState("success");
    setActiveStep("recovery");
  }

  if (!initialData.workspace) {
    return (
      <OnboardingEmptyState
        title="No workspace available"
        message="Seed or create a workspace in the API before data onboarding can load workspace-scoped sources."
      />
    );
  }

  return (
    <div className="space-y-6">
      <DataOnboardingHeader
        apiBaseUrl={initialData.apiBaseUrl}
        workspace={selectedWorkspace}
        workspaces={initialData.workspaces}
        selection={selection}
        steps={steps}
        activeStep={activeStep}
        onStepChange={setActiveStep}
        onWorkspaceChange={(workspaceId) =>
          setSelection({
            workspaceId,
            sourceId: null,
            symbolIds: [],
            timeframes: selection.timeframes,
          })
        }
      />
      {(workflowError || initialData.failures.length > 0) && (
        <OnboardingErrorState
          title="Backend state needs attention"
          message={workflowError || initialData.failures[0]?.message || "Some onboarding endpoints did not respond."}
          failures={initialData.failures}
        />
      )}
      <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="surface h-fit rounded-lg p-4">
          <div className="space-y-2">
            {steps.map((step, index) => (
              <button
                key={step.key}
                type="button"
                onClick={() => setActiveStep(step.key)}
                className={`w-full rounded-md px-3 py-2 text-left text-sm font-medium ${
                  step.key === activeStep
                    ? "bg-teal-50 text-teal-800 dark:bg-teal-950 dark:text-teal-100"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`}
              >
                <span className="mr-2 text-xs text-slate-500">{index + 1}</span>
                {step.label}
              </button>
            ))}
          </div>
        </aside>
        <div className="space-y-6">
          {activeStep === "data_source" && (
            <DataSourceStep
              dataSources={dataSources}
              selectedSourceId={selection.sourceId}
              loadState={sourceLoadState}
              onSourceChange={(sourceId) => setSelection((current) => ({ ...current, sourceId }))}
              onCreateSource={handleCreateSource}
            />
          )}
          {activeStep === "symbols" && (
            <SymbolSelectionStep
              symbols={initialData.symbols}
              selectedSymbolIds={selection.symbolIds}
              onChange={(symbolIds) => setSelection((current) => ({ ...current, symbolIds }))}
            />
          )}
          {activeStep === "timeframes" && (
            <TimeframeSelectionStep
              timeframes={[...onboardingTimeframes]}
              selectedTimeframes={selection.timeframes}
              onChange={(timeframes) => setSelection((current) => ({ ...current, timeframes }))}
            />
          )}
          {activeStep === "freshness" && (
            <FreshnessCheckStep
              rows={healthRows}
              validation={validation}
              loadState={freshnessState}
              selectedSource={selectedSource}
              onRunFreshnessCheck={handleRunFreshnessCheck}
              canRun={canRunFreshness}
            />
          )}
          {activeStep === "gaps" && (
            <GapDetectionStep
              rows={gapRows}
              healthRows={healthRows}
              loadState={gapState}
              onDetectGaps={handleDetectGaps}
            />
          )}
          {activeStep === "recovery" && (
            <RecoveryPlanStep
              rows={recoveryRows}
              gapRows={gapRows}
              loadState={recoveryState}
              onPrepareRecovery={handlePrepareRecovery}
            />
          )}
          {activeStep === "summary" && (
            <OnboardingSummary
              healthRows={healthRows}
              gapRows={gapRows}
              recoveryRows={recoveryRows}
              nextBackendActions={safeNextSteps}
            />
          )}
          <div className="flex flex-wrap justify-between gap-3">
            <button
              type="button"
              className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-medium text-slate-600 disabled:opacity-40 dark:text-slate-300"
              disabled={stepIndex <= 0}
              onClick={() => setActiveStep(steps[Math.max(stepIndex - 1, 0)].key)}
            >
              Previous
            </button>
            <button
              type="button"
              className="rounded-md bg-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
              disabled={stepIndex >= steps.length - 1}
              onClick={() => setActiveStep(steps[Math.min(stepIndex + 1, steps.length - 1)].key)}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

async function loadHealthRow(params: {
  workspaceId: UUID;
  sourceId: UUID | null;
  symbol: SymbolRead;
  timeframe: string;
  memorySnapshots: MarketMemorySnapshot[];
}): Promise<DataHealthRow> {
  const [latestResult, liveResult, pollingResult] = await Promise.all([
    getLatestCandle({
      workspaceId: params.workspaceId,
      symbolId: params.symbol.id,
      sourceId: params.sourceId,
      timeframe: params.timeframe,
      isFinal: true,
    }),
    listLiveSubscriptions({ workspaceId: params.workspaceId, symbolId: params.symbol.id }),
    listProviderPollingRequests({
      workspaceId: params.workspaceId,
      symbolId: params.symbol.id,
      sourceId: params.sourceId || undefined,
    }),
  ]);
  const latestFinalCandle = latestResult.ok ? latestResult.data : null;
  const window = buildHealthWindow(params.timeframe, latestFinalCandle?.timestamp || null);
  const [countResult, qualityResult, dataQualityResult] = await Promise.all([
    countCandles({
      workspaceId: params.workspaceId,
      symbolId: params.symbol.id,
      sourceId: params.sourceId,
      timeframe: params.timeframe,
      startTime: window.startTime,
      endTime: window.endTime,
    }),
    getCandleQuality({
      workspaceId: params.workspaceId,
      symbolId: params.symbol.id,
      sourceId: params.sourceId,
      timeframe: params.timeframe,
      startTime: window.startTime,
      endTime: window.endTime,
    }),
    runCandleRangeQuality({
      workspaceId: params.workspaceId,
      symbolId: params.symbol.id,
      sourceId: params.sourceId,
      timeframe: params.timeframe,
      startTime: window.startTime,
      endTime: window.endTime,
    }),
  ]);
  const errors = [
    resultError(latestResult),
    resultError(liveResult),
    resultError(pollingResult),
    resultError(countResult),
    resultError(qualityResult),
    resultError(dataQualityResult),
  ].filter((error): error is ApiError => Boolean(error));
  return composeDataHealth({
    target: {
      workspaceId: params.workspaceId,
      sourceId: params.sourceId,
      symbol: params.symbol,
      timeframe: params.timeframe,
      startTime: window.startTime,
      endTime: window.endTime,
    },
    latestFinalCandle,
    candleCount: countResult.ok ? countResult.data : null,
    candleQuality: qualityResult.ok ? qualityResult.data : null,
    dataQualityRun: dataQualityResult.ok ? dataQualityResult.data : null,
    marketMemory: findMemorySnapshot(
      params.memorySnapshots,
      params.symbol.id,
      params.sourceId,
      params.timeframe,
    ),
    liveSubscription: liveResult.ok
      ? latestByDate(
          liveResult.data.filter(
            (subscription) =>
              subscription.timeframe === params.timeframe &&
              (!params.sourceId || subscription.source_id === params.sourceId),
          ),
          "updated_at",
        )
      : null,
    providerPollingRequest: pollingResult.ok
      ? latestByDate(
          pollingResult.data.filter((request) => request.timeframe === params.timeframe),
          "created_at",
        )
      : null,
    errors,
  });
}

function initialSelection(initialData: OnboardingInitialData): OnboardingSelection {
  const params = typeof window === "undefined" ? null : new URLSearchParams(window.location.search);
  const workspaceId = params?.get("workspaceId") || initialData.workspace?.id || null;
  const sourceId = params?.get("sourceId") || initialData.dataSources[0]?.id || null;
  const symbolIds = splitQuery(params?.get("symbolIds")).filter((id) =>
    initialData.symbols.some((symbol) => symbol.id === id),
  );
  const timeframes = splitQuery(params?.get("timeframes")).filter((timeframe) =>
    isSupportedTimeframe(timeframe),
  );
  return {
    workspaceId,
    sourceId,
    symbolIds,
    timeframes: timeframes.length > 0 ? timeframes : ["1m", "5m", "15m"],
  };
}

function readStoredSelection(initialData: OnboardingInitialData): OnboardingSelection | null {
  try {
    const rawValue = window.localStorage.getItem(storageKey);
    if (!rawValue) {
      return null;
    }
    const parsed = JSON.parse(rawValue) as Partial<OnboardingSelection>;
    const workspaceId =
      parsed.workspaceId && initialData.workspaces.some((workspace) => workspace.id === parsed.workspaceId)
        ? parsed.workspaceId
        : initialData.workspace?.id || null;
    return {
      workspaceId,
      sourceId: typeof parsed.sourceId === "string" ? parsed.sourceId : null,
      symbolIds: Array.isArray(parsed.symbolIds)
        ? parsed.symbolIds.filter((id): id is string => typeof id === "string")
        : [],
      timeframes: Array.isArray(parsed.timeframes)
        ? parsed.timeframes.filter((timeframe): timeframe is string =>
            isSupportedTimeframe(timeframe),
          )
        : ["1m", "5m", "15m"],
    };
  } catch {
    return null;
  }
}

function persistSelection(selection: OnboardingSelection) {
  window.localStorage.setItem(storageKey, JSON.stringify(selection));
  const params = new URLSearchParams(window.location.search);
  setOrDelete(params, "workspaceId", selection.workspaceId);
  setOrDelete(params, "sourceId", selection.sourceId);
  setOrDelete(params, "symbolIds", selection.symbolIds.join(","));
  setOrDelete(params, "timeframes", selection.timeframes.join(","));
  const query = params.toString();
  window.history.replaceState(null, "", query ? `?${query}` : window.location.pathname);
}

function validateSelection(selection: OnboardingSelection): string[] {
  const issues: string[] = [];
  if (!selection.workspaceId) {
    issues.push("Workspace is required");
  }
  if (!selection.sourceId) {
    issues.push("Data source is required");
  }
  if (selection.symbolIds.length === 0) {
    issues.push("At least one symbol is required");
  }
  if (selection.timeframes.length === 0) {
    issues.push("At least one timeframe is required");
  }
  return issues;
}

function splitQuery(value: string | null | undefined): string[] {
  return value ? value.split(",").map((item) => item.trim()).filter(Boolean) : [];
}

function isSupportedTimeframe(value: string): boolean {
  return (onboardingTimeframes as readonly string[]).includes(value);
}

function setOrDelete(params: URLSearchParams, key: string, value: string | null | undefined) {
  if (value) {
    params.set(key, value);
    return;
  }
  params.delete(key);
}

function buildHealthWindow(timeframe: string, latestTimestamp: string | null): {
  startTime: string;
  endTime: string;
} {
  const duration = timeframeDurationsMs[timeframe] || timeframeDurationsMs["1m"];
  const rawEnd = latestTimestamp ? new Date(latestTimestamp).getTime() : Date.now();
  const end = Math.floor(rawEnd / duration) * duration;
  const start = end - (healthLookbackCandles - 1) * duration;
  return {
    startTime: new Date(start).toISOString(),
    endTime: new Date(end).toISOString(),
  };
}

function findMemorySnapshot(
  snapshots: MarketMemorySnapshot[],
  symbolId: UUID,
  sourceId: UUID | null,
  timeframe: string,
): MarketMemorySnapshot | null {
  return (
    snapshots.find(
      (snapshot) =>
        snapshot.symbol_id === symbolId &&
        snapshot.timeframe === timeframe &&
        (sourceId ? snapshot.source_id === sourceId : true),
    ) || null
  );
}

function latestByDate<T>(values: T[], fieldName: keyof T): T | null {
  return (
    [...values].sort((left, right) => {
      const leftTime = new Date(String(left[fieldName] || "")).getTime();
      const rightTime = new Date(String(right[fieldName] || "")).getTime();
      return rightTime - leftTime;
    })[0] || null
  );
}

function resultError(result: { ok: boolean; error?: ApiError }): ApiError | null {
  if (result.ok || !result.error || result.error.missing) {
    return null;
  }
  return result.error;
}

function nextBackendActions(
  healthRows: DataHealthRow[],
  gapRows: GapDetectionRow[],
  recoveryRows: RecoveryPreparationRow[],
): string[] {
  const actions: string[] = [];
  if (healthRows.some((row) => row.status === "recovery_needed" || row.status === "missing_data")) {
    actions.push("Prepare recovery plan for missing final candles.");
  }
  if (healthRows.some((row) => row.status === "stale")) {
    actions.push("Review stale live feed subscriptions or provider polling cadence.");
  }
  if (gapRows.some((row) => row.items.some((item) => item.recovery_method === "manual_import"))) {
    actions.push("Use server-side import configuration for manual recovery items.");
  }
  if (recoveryRows.some((row) => row.requests.length > 0)) {
    actions.push("Review prepared provider polling requests before backend execution.");
  }
  if (actions.length === 0 && healthRows.length > 0) {
    actions.push("Use ready symbols for deterministic analysis workflows.");
  }
  return actions;
}
