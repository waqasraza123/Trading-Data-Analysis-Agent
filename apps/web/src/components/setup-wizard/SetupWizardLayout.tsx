"use client";

import { useState } from "react";
import Link from "next/link";
import { CredentialStep } from "./CredentialStep";
import { DataSourceStep } from "./DataSourceStep";
import { DemoDataStep } from "./DemoDataStep";
import { FirstScanStep } from "./FirstScanStep";
import { PreferenceProfileStep } from "./PreferenceProfileStep";
import { ReadinessStep } from "./ReadinessStep";
import { ScannerPresetStep } from "./ScannerPresetStep";
import { SetupProgress } from "./SetupProgress";
import { SetupSummary } from "./SetupSummary";
import { SymbolsStep } from "./SymbolsStep";
import { UserStep } from "./UserStep";
import { WatchlistStep } from "./WatchlistStep";
import { WorkspaceStep } from "./WorkspaceStep";
import {
  completeWorkspaceSetupStep,
  createSetupDemoWorkspace,
  finishWorkspaceSetup,
  skipWorkspaceSetupStep,
  startWorkspaceSetup,
} from "@/lib/api/workspaceSetup";
import type {
  SetupMutationState,
  SetupWizardInitialData,
  SetupWizardLocalSelection,
  SetupWizardStepProps,
  WorkspaceSetupRun,
  WorkspaceSetupStepKey,
} from "@/lib/setup-wizard/types";

type SetupWizardLayoutProps = {
  initialData: SetupWizardInitialData;
};

export function SetupWizardLayout({ initialData }: SetupWizardLayoutProps) {
  const [run, setRun] = useState<WorkspaceSetupRun | null>(null);
  const [activeStep, setActiveStep] = useState<WorkspaceSetupStepKey>("workspace");
  const [mutation, setMutation] = useState<SetupMutationState>({ status: "idle", message: null });
  const [selection, setSelection] = useState<SetupWizardLocalSelection>({
    workspaceId: initialData.selectedWorkspaceId,
    symbolIds: initialData.symbols
      .filter((symbol) => symbol.market_type === "crypto")
      .slice(0, 2)
      .map((symbol) => symbol.id),
    timeframes: ["1m", "5m", "15m"],
    sourceId: initialData.dataSources[0]?.id || null,
    watchlistId: null,
    scanConfigId: initialData.scanConfigs[0]?.id || null,
  });

  const currentStep = run?.current_step || activeStep;
  const sharedProps = {
    run,
    initialData,
    selectedWorkspaceId: selection.workspaceId,
    selectedSymbolIds: selection.symbolIds,
    selectedTimeframes: selection.timeframes,
    selectedSourceId: selection.sourceId,
    selectedWatchlistId: selection.watchlistId,
    selectedScanConfigId: selection.scanConfigId,
    mutation,
    onComplete: completeStep,
    onSkip: skipStep,
    onLocalSelectionChange: updateSelection,
  };

  async function startWizard() {
    setMutation({ status: "pending", message: null });
    const result = await startWorkspaceSetup({
      workspace_id: selection.workspaceId || undefined,
      initial_context_json: { source: "web_setup_wizard" },
    });
    if (!result.ok) {
      setMutation({ status: "error", message: result.error.message });
      return;
    }
    setRun(result.data);
    setActiveStep(result.data.current_step);
    setMutation({ status: "success", message: "Setup run started." });
  }

  async function createDemo() {
    setMutation({ status: "pending", message: null });
    const result = await createSetupDemoWorkspace({
      workspace_name: "Demo Market Workspace",
      operator_email: "operator@example.test",
      operator_name: "Demo Operator",
      market_type: "crypto",
      symbol_codes: ["BTCUSDT", "ETHUSDT"],
      timeframes: ["1m"],
      seed_demo_data: true,
    });
    if (!result.ok) {
      setMutation({ status: "error", message: result.error.message });
      return;
    }
    setRun(result.data.setup_run);
    setActiveStep(result.data.setup_run.current_step);
    setSelection((current) => ({
      ...current,
      workspaceId: result.data.workspace_id,
      scanConfigId: result.data.scan_config_id,
      watchlistId: result.data.watchlist_id,
    }));
    setMutation({ status: "success", message: "Demo workspace created." });
  }

  async function completeStep(stepKey: WorkspaceSetupStepKey, input: Record<string, unknown>) {
    if (!run) {
      setMutation({ status: "error", message: "Start setup before saving a step." });
      return;
    }
    setMutation({ status: "pending", message: null });
    const result = await completeWorkspaceSetupStep(run.id, stepKey, input);
    if (!result.ok) {
      setMutation({ status: "error", message: result.error.message });
      return;
    }
    applyRun(result.data);
    setMutation({ status: "success", message: `${stepLabel(stepKey)} saved.` });
  }

  async function skipStep(stepKey: WorkspaceSetupStepKey) {
    if (!run) {
      setMutation({ status: "error", message: "Start setup before skipping a step." });
      return;
    }
    setMutation({ status: "pending", message: null });
    const result = await skipWorkspaceSetupStep(run.id, stepKey);
    if (!result.ok) {
      setMutation({ status: "error", message: result.error.message });
      return;
    }
    applyRun(result.data);
    setMutation({ status: "success", message: `${stepLabel(stepKey)} skipped.` });
  }

  async function finishWizard() {
    if (!run) {
      return;
    }
    setMutation({ status: "pending", message: null });
    const result = await finishWorkspaceSetup(run.id);
    if (!result.ok) {
      setMutation({ status: "error", message: result.error.message });
      return;
    }
    applyRun(result.data);
    setMutation({ status: "success", message: "Setup finished." });
  }

  function applyRun(nextRun: WorkspaceSetupRun) {
    setRun(nextRun);
    setActiveStep(nextRun.current_step);
    setSelection((current) => ({
      ...current,
      workspaceId: nextRun.workspace_id || current.workspaceId,
      sourceId: stringValue(nextRun.result_json.dataSourceId) || current.sourceId,
      watchlistId: stringValue(nextRun.result_json.watchlistId) || current.watchlistId,
      scanConfigId: stringValue(nextRun.result_json.scanConfigId) || current.scanConfigId,
      symbolIds: stringArray(nextRun.result_json.symbolIds) || current.symbolIds,
    }));
  }

  function updateSelection(nextSelection: Partial<SetupWizardLocalSelection>) {
    setSelection((current) => ({ ...current, ...nextSelection }));
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">Guided setup</p>
          <h2 className="mt-1 text-3xl font-semibold text-[var(--strong)]">Workspace setup wizard</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            Configure a deterministic market-analysis workspace, optional demo data, readiness, and an explicit first scan.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold" href={selection.workspaceId ? `/onboarding?workspaceId=${selection.workspaceId}` : "/onboarding"}>
            Onboarding status
          </Link>
          <button className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold" disabled={mutation.status === "pending"} type="button" onClick={startWizard}>
            {run ? "Start new run" : "Start setup"}
          </button>
          <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={mutation.status === "pending"} type="button" onClick={createDemo}>
            Demo workspace
          </button>
          {run && (
            <button className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold" disabled={mutation.status === "pending"} type="button" onClick={finishWizard}>
              Finish
            </button>
          )}
        </div>
      </section>
      {mutation.message && (
        <p className={`rounded-md px-3 py-2 text-sm ${mutation.status === "error" ? "bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-100" : "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-100"}`}>
          {mutation.message}
        </p>
      )}
      {initialData.failures.length > 0 && (
        <div className="surface rounded-lg p-4">
          <p className="text-sm font-semibold text-[var(--strong)]">Backend state</p>
          <div className="mt-3 grid gap-2 md:grid-cols-2">
            {initialData.failures.map((failure) => (
              <p key={`${failure.label}-${failure.status}`} className="muted-surface rounded-md p-3 text-sm text-slate-600 dark:text-slate-300">
                {failure.label}: {failure.message}
              </p>
            ))}
          </div>
        </div>
      )}
      <SetupProgress run={run} activeStep={currentStep} onSelectStep={setActiveStep} />
      {!run ? (
        <div className="surface rounded-lg p-6 text-sm leading-6 text-slate-600 dark:text-slate-300">
          Start a setup run or create a demo workspace. The wizard stores setup progress in the backend and keeps provider secrets out of setup run payloads.
        </div>
      ) : (
        renderStep(activeStep, sharedProps)
      )}
      <SetupSummary run={run} />
    </div>
  );
}

function renderStep(step: WorkspaceSetupStepKey, props: SetupWizardStepProps) {
  if (step === "workspace") return <WorkspaceStep {...props} />;
  if (step === "user") return <UserStep {...props} />;
  if (step === "symbols") return <SymbolsStep {...props} />;
  if (step === "data_source") return <DataSourceStep {...props} />;
  if (step === "credential_reference") return <CredentialStep {...props} />;
  if (step === "watchlist") return <WatchlistStep {...props} />;
  if (step === "scanner_preset") return <ScannerPresetStep {...props} />;
  if (step === "preference_profile") return <PreferenceProfileStep {...props} />;
  if (step === "demo_data") return <DemoDataStep {...props} />;
  if (step === "readiness_check") return <ReadinessStep {...props} />;
  return <FirstScanStep {...props} />;
}

function stepLabel(step: WorkspaceSetupStepKey): string {
  return step.replaceAll("_", " ");
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

function stringArray(value: unknown): string[] | null {
  return Array.isArray(value) && value.every((item) => typeof item === "string") ? value : null;
}
