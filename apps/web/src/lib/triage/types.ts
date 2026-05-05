import type {
  ApiError,
  DecisionReadinessAssessmentResponse,
  IntelligenceReport,
  JsonRecord,
  MarketMemorySnapshot,
  SignalPriorityScore,
  SetupContext,
  SignalClassification,
  SignalOutcome,
  SymbolRead,
  UUID,
  Workspace,
} from "@/lib/api/types";
import type { PreferenceProfile } from "@/lib/preferences/types";

export type TriageColumnKey =
  | "high_quality_context"
  | "needs_confirmation"
  | "conflicted"
  | "avoid_no_directional_signal"
  | "stale_data_issue"
  | "review_required";

export type TriageFilterState = {
  workspaceId?: UUID;
  symbolSearch?: string;
  symbolId?: UUID;
  timeframe?: string;
  bias?: string;
  confidence?: string;
  column?: TriageColumnKey;
  freshness?: string;
  profileKey?: string;
  preferenceProfileId?: UUID;
  sort?: "priority" | "freshness" | "confidence" | "created";
  onlyFresh: boolean;
  onlyReviewRequired: boolean;
};

export type TriageFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export type TriageReason = {
  label: string;
  tone: "neutral" | "good" | "warning" | "danger" | "info";
};

export type TriageClassification = {
  column: TriageColumnKey;
  mainReason: TriageReason;
  reasons: TriageReason[];
};

export type IntelligenceQualityFinding = {
  severity: string;
  code: string;
  title: string;
  message: string;
  finding_type?: string;
};

export type IntelligenceQualityResponse = {
  quality_run: {
    quality_label: string;
    status: string;
    summary: string;
  };
  findings: IntelligenceQualityFinding[];
  shadow_classifications: Array<{
    agreement_with_final: string;
    disagreement_reason: string | null;
  }>;
};

export type ScenarioReasoningResponse = {
  reasoning_run: {
    status: string;
    safety_status: string;
    grounding_status: string;
    blocked_terms_json: string[];
    grounding_issues_json: string[];
  };
  summary: string;
  scenarios: Array<{
    scenario_label: string;
    conflicting_evidence: string[];
    next_observations: string[];
    suggested_backend_actions: string[];
    risk_notes: string[];
  }>;
  limitations: string[];
};

export type OperatorReviewItem = {
  id: UUID;
  related_signal_id: UUID | null;
  related_analysis_run_id: UUID | null;
  priority: string;
  status: string;
  title: string;
  summary: string;
  reason_code: string | null;
};

export type TriageActionItem = {
  id: UUID;
  workspace_id: UUID;
  signal_id: UUID | null;
  analysis_run_id: UUID | null;
  reasoning_run_id: UUID | null;
  action_type: string;
  status: string;
  priority: string;
  due_at: string | null;
};

export type TriageCandidate = {
  id: UUID;
  signal: SignalClassification;
  symbol: SymbolRead | null;
  memory: MarketMemorySnapshot | null;
  priorityScore: SignalPriorityScore | null;
  setupContext: SetupContext | null;
  outcomes: SignalOutcome[];
  readiness: DecisionReadinessAssessmentResponse | null;
  report: IntelligenceReport | null;
  quality: IntelligenceQualityResponse | null;
  reasoning: ScenarioReasoningResponse | null;
  reviews: OperatorReviewItem[];
  actionItems: TriageActionItem[];
  missingContexts: string[];
  classification: TriageClassification;
};

export type TriageBoardData = {
  appName: string;
  apiBaseUrl: string;
  requestedWorkspaceId: UUID | null;
  workspace: Workspace | null;
  workspaces: Workspace[];
  symbols: SymbolRead[];
  preferenceProfiles: PreferenceProfile[];
  selectedPreferenceProfile: PreferenceProfile | null;
  filters: TriageFilterState;
  candidates: TriageCandidate[];
  allCandidates: TriageCandidate[];
  unfilteredCandidateCount: number;
  failures: TriageFailure[];
  lastLoadedAt: string;
};

export type TriageArtifactInput = {
  signal: SignalClassification;
  memory: MarketMemorySnapshot | null;
  priorityScore: SignalPriorityScore | null;
  setupContext: SetupContext | null;
  outcomes: SignalOutcome[];
  readiness: DecisionReadinessAssessmentResponse | null;
  report: IntelligenceReport | null;
  quality: IntelligenceQualityResponse | null;
  reasoning: ScenarioReasoningResponse | null;
  reviews: OperatorReviewItem[];
  actionItems: TriageActionItem[];
  missingContexts: string[];
};

export type ReportSections = JsonRecord;
export type OptionalApiFailure = ApiError | null;
