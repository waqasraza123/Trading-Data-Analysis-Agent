import type {
  DataSource,
  JsonRecord,
  ScheduledScanConfig,
  SymbolRead,
  UUID,
  Workspace,
} from "@/lib/api/types";
import type { ProviderCredentialRef } from "@/lib/data-onboarding/types";
import type { ProductReadinessRun } from "@/lib/readiness/types";
import type { ScannerPreset, ScheduledScanRun } from "@/lib/scanner/types";

export type WorkspaceSetupStatus =
  | "draft"
  | "running"
  | "completed"
  | "completed_with_warnings"
  | "failed"
  | "cancelled";

export type WorkspaceSetupStepKey =
  | "workspace"
  | "user"
  | "symbols"
  | "data_source"
  | "credential_reference"
  | "watchlist"
  | "scanner_preset"
  | "preference_profile"
  | "demo_data"
  | "readiness_check"
  | "first_scan";

export type WorkspaceSetupStepStatus = "pending" | "completed" | "skipped" | "failed";

export type WorkspaceSetupStepResult = {
  id: UUID;
  setup_run_id: UUID;
  step_key: WorkspaceSetupStepKey;
  status: WorkspaceSetupStepStatus;
  input_json: JsonRecord;
  output_json: JsonRecord | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type WorkspaceSetupRun = {
  id: UUID;
  workspace_id: UUID | null;
  user_id: UUID | null;
  status: WorkspaceSetupStatus;
  setup_version: string;
  current_step: WorkspaceSetupStepKey;
  completed_steps_json: string[];
  skipped_steps_json: string[];
  failed_steps_json: string[];
  result_json: JsonRecord;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  step_results: WorkspaceSetupStepResult[];
};

export type SetupWizardInitialData = {
  appName: string;
  workspaces: Workspace[];
  symbols: SymbolRead[];
  dataSources: DataSource[];
  providerCredentialRefs: ProviderCredentialRef[];
  scannerPresets: ScannerPreset[];
  scanConfigs: ScheduledScanConfig[];
  readinessRun: ProductReadinessRun | null;
  failures: SetupWizardFailure[];
  selectedWorkspaceId: UUID | null;
};

export type SetupWizardFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export type SetupMutationState = {
  status: "idle" | "pending" | "success" | "error";
  message: string | null;
};

export type SetupWizardStepProps = {
  run: WorkspaceSetupRun | null;
  initialData: SetupWizardInitialData;
  selectedWorkspaceId: UUID | null;
  selectedSymbolIds: UUID[];
  selectedTimeframes: string[];
  selectedSourceId: UUID | null;
  selectedWatchlistId: UUID | null;
  selectedScanConfigId: UUID | null;
  mutation: SetupMutationState;
  onComplete: (stepKey: WorkspaceSetupStepKey, input: Record<string, unknown>) => Promise<void>;
  onSkip: (stepKey: WorkspaceSetupStepKey) => Promise<void>;
  onLocalSelectionChange: (selection: Partial<SetupWizardLocalSelection>) => void;
};

export type SetupWizardLocalSelection = {
  workspaceId: UUID | null;
  symbolIds: UUID[];
  timeframes: string[];
  sourceId: UUID | null;
  watchlistId: UUID | null;
  scanConfigId: UUID | null;
};

export type SetupDemoWorkspaceResponse = {
  setup_run: WorkspaceSetupRun;
  workspace_id: UUID | null;
  user_id: UUID | null;
  watchlist_id: UUID | null;
  scan_config_id: UUID | null;
  readiness_run_id: UUID | null;
};

export type SetupScanRunResult = ScheduledScanRun;
