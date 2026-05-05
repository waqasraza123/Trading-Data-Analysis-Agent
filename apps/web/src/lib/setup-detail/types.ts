import type {
  AuditTimeline,
  ContextRead,
  CrossAssetContextResult,
  CrossAssetContextRun,
  DecisionReadinessAssessmentResponse,
  HistoricalCaseSearchRead,
  IntelligenceQualityResponse,
  IntelligenceReport,
  JournalEntry,
  JsonRecord,
  MultiTimeframeContext,
  ScenarioReasoningResponse,
  SetupContext,
  SignalClassification,
  SignalConfidenceComponent,
  SignalEvidence,
  SignalOutcome,
  SignalRiskNote,
  UUID,
} from "@/lib/api/types";
import type { SetupChartContext } from "@/lib/api/setupChart";

export type SetupDetailFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export type SetupDetailData = {
  appName: string;
  apiBaseUrl: string;
  signalId: UUID;
  signal: SignalClassification | null;
  report: IntelligenceReport | null;
  setupContext: SetupContext | null;
  outcomes: SignalOutcome[];
  readiness: DecisionReadinessAssessmentResponse | null;
  marketRegime: ContextRead | null;
  marketSession: ContextRead | null;
  auditTimeline: AuditTimeline | null;
  quality: IntelligenceQualityResponse | null;
  historicalCases: HistoricalCaseSearchRead | null;
  reasoning: ScenarioReasoningResponse | null;
  multiTimeframeContext: MultiTimeframeContext | null;
  crossAssetContext: CrossAssetContextRun | null;
  crossAssetResults: CrossAssetContextResult[];
  journalEntries: JournalEntry[];
  setupChart: SetupChartContext;
  failures: SetupDetailFailure[];
  lastUpdatedAt: string;
};

export type DetailItem = {
  label: string;
  value: string;
  detail?: string;
  tone?: "neutral" | "good" | "warning" | "danger" | "info";
};

export type SetupDetailHeaderModel = {
  symbol: string;
  timeframe: string;
  bias: string;
  pattern: string;
  confidenceLabel: string;
  confidenceScore: string | null;
  setupQualityLabel: string;
  setupQualityScore: string | null;
  latestFinalCandleTime: string | null;
  dataFreshness: string;
  summary: string;
};

export type EvidenceGroup = {
  type: string;
  supporting: SignalEvidence[];
  conflicting: SignalEvidence[];
  neutral: SignalEvidence[];
};

export type SetupDetailViewModel = {
  header: SetupDetailHeaderModel;
  signal: SignalClassification | null;
  report: IntelligenceReport | null;
  setupContext: SetupContext | null;
  evidenceGroups: EvidenceGroup[];
  confidenceComponents: SignalConfidenceComponent[];
  riskNotes: SignalRiskNote[];
  outcomes: SignalOutcome[];
  readiness: DecisionReadinessAssessmentResponse | null;
  quality: IntelligenceQualityResponse | null;
  historicalCases: HistoricalCaseSearchRead | null;
  reasoning: ScenarioReasoningResponse | null;
  auditTimeline: AuditTimeline | null;
  marketRegime: ContextRead | null;
  marketSession: ContextRead | null;
  multiTimeframeContext: MultiTimeframeContext | null;
  crossAssetContext: CrossAssetContextRun | null;
  crossAssetResults: CrossAssetContextResult[];
  journalEntries: JournalEntry[];
  setupChart: SetupChartContext;
  actionPlanSection: JsonRecord | null;
  humanReviewSection: JsonRecord | null;
  reportMissingSections: string[];
  reportWarnings: string[];
  failures: SetupDetailFailure[];
};
