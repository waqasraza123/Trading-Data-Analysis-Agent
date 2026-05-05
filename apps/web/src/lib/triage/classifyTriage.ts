import { reason } from "./labels";
import type { TriageArtifactInput, TriageClassification, TriageColumnKey, TriageReason } from "./types";

const directionalBiases = new Set(["bullish", "bearish"]);
const highConfidenceLabels = new Set(["high", "strong"]);
const mediumConfidenceLabels = new Set(["medium", "acceptable"]);
const acceptableSetupLabels = new Set(["acceptable", "strong"]);
const freshLabels = new Set(["fresh", "current"]);
const degradedFreshnessLabels = new Set(["stale", "degraded", "poor", "missing"]);
const criticalSeverities = new Set(["critical", "blocker", "failed"]);
const severeRiskSeverities = new Set(["critical", "high"]);
const openReviewStatuses = new Set(["open", "pending", "assigned", "in_review"]);

export function classifyTriage(input: TriageArtifactInput): TriageClassification {
  const reasons = collectReasons(input);
  if (isReviewRequired(input)) {
    return result("review_required", reason("Review required"), reasons);
  }
  if (hasStaleDataIssue(input)) {
    return result("stale_data_issue", reason("Stale data"), reasons);
  }
  if (hasConflictedEvidence(input)) {
    return result("conflicted", reason("Conflicted"), reasons);
  }
  if (isAvoidOrNoDirectional(input)) {
    return result("avoid_no_directional_signal", avoidReason(input), reasons);
  }
  if (needsConfirmation(input)) {
    return result("needs_confirmation", reason("Needs confirmation"), reasons);
  }
  if (hasHighQualityContext(input)) {
    return result("high_quality_context", reason("Review first"), reasons);
  }
  return result("review_required", reason("Review required"), reasons);
}

function result(column: TriageColumnKey, mainReason: TriageReason, reasons: TriageReason[]): TriageClassification {
  const uniqueReasons = dedupeReasons([mainReason, ...reasons]);
  return {
    column,
    mainReason,
    reasons: uniqueReasons,
  };
}

function collectReasons(input: TriageArtifactInput): TriageReason[] {
  const reasons: TriageReason[] = [];
  if (input.memory?.freshness_label) {
    reasons.push(reason(freshLabels.has(normalize(input.memory.freshness_label)) ? "Fresh data" : "Stale data"));
  }
  if (input.setupContext?.setup_quality_label) {
    reasons.push(reason(`${input.setupContext.setup_quality_label} setup context`));
  }
  if (input.readiness?.assessment.readiness_label) {
    reasons.push(reason(`${input.readiness.assessment.readiness_label} readiness`));
  }
  if (input.quality?.findings.length) {
    reasons.push(reason(hasCriticalQualityFinding(input) ? "Critical quality finding" : "Quality finding"));
  }
  if (input.reasoning?.reasoning_run.grounding_status && normalize(input.reasoning.reasoning_run.grounding_status) !== "passed") {
    reasons.push(reason("Grounding issue"));
  }
  if (input.missingContexts.length) {
    reasons.push(reason("Missing context"));
  }
  return reasons;
}

function hasHighQualityContext(input: TriageArtifactInput): boolean {
  return (
    isDirectional(input) &&
    highConfidenceLabels.has(normalize(input.signal.signal.confidence_label)) &&
    hasAcceptableSetup(input) &&
    hasFreshData(input) &&
    !hasSevereRisk(input) &&
    hasUsableReadiness(input) &&
    !hasCriticalQualityFinding(input)
  );
}

function needsConfirmation(input: TriageArtifactInput): boolean {
  return (
    mediumConfidenceLabels.has(normalize(input.signal.signal.confidence_label)) ||
    (input.setupContext?.wait_conditions_json.length || 0) > 0 ||
    input.outcomes.length === 0 ||
    hasMixedTimeframeContext(input) ||
    input.actionItems.some((item) => normalize(item.action_type) === "evaluate_outcome_after_horizon")
  );
}

function hasConflictedEvidence(input: TriageArtifactInput): boolean {
  return (
    input.quality?.findings.some((finding) => normalize(finding.severity) !== "critical") === true ||
    input.quality?.shadow_classifications.some((shadow) => normalize(shadow.agreement_with_final) !== "agree") === true ||
    input.reasoning?.scenarios.some((scenario) => scenario.conflicting_evidence.length > 0) === true ||
    (input.reasoning?.reasoning_run.grounding_issues_json.length || 0) > 0 ||
    input.signal.evidence.some((item) => hasEvidenceConflict(item.direction, input.signal.signal.bias)) ||
    hasReportConflict(input)
  );
}

function isAvoidOrNoDirectional(input: TriageArtifactInput): boolean {
  const status = normalize(input.signal.signal.classification_status);
  const bias = normalize(input.signal.signal.bias);
  const noSignalReason = normalize(input.signal.signal.no_signal_reason);
  const confidenceScore = Number(input.signal.signal.confidence_score);
  return (
    status === "no_signal" ||
    bias === "neutral" ||
    bias === "unclear" ||
    noSignalReason.includes("chop") ||
    noSignalReason.includes("range") ||
    noSignalReason.includes("fakeout") ||
    input.signal.signal.range_state === "range" ||
    (Number.isFinite(confidenceScore) && confidenceScore < 0.4) ||
    (input.setupContext?.avoid_reasons_json.length || 0) > 0
  );
}

function hasStaleDataIssue(input: TriageArtifactInput): boolean {
  return (
    !input.memory ||
    degradedFreshnessLabels.has(normalize(input.memory.freshness_label)) ||
    degradedFreshnessLabels.has(normalize(input.memory.data_quality_label)) ||
    input.memory.warnings_json.some((warning) => warningText(warning).includes("missing")) ||
    input.memory.warnings_json.some((warning) => warningText(warning).includes("gap")) ||
    input.memory.warnings_json.some((warning) => warningText(warning).includes("subscription stale")) ||
    (input.setupContext?.data_quality_warnings_json.length || 0) > 0
  );
}

function isReviewRequired(input: TriageArtifactInput): boolean {
  const readinessLabel = normalize(input.readiness?.assessment.readiness_label);
  return (
    readinessLabel === "blocked" ||
    readinessLabel === "not_ready" ||
    input.reviews.some((review) => openReviewStatuses.has(normalize(review.status))) ||
    hasCriticalQualityFinding(input) ||
    normalize(input.reasoning?.reasoning_run.safety_status) === "blocked" ||
    (input.reasoning?.reasoning_run.blocked_terms_json.length || 0) > 0 ||
    hasScreenshotReviewNeed(input)
  );
}

function isDirectional(input: TriageArtifactInput): boolean {
  return (
    normalize(input.signal.signal.classification_status) === "signal" &&
    directionalBiases.has(normalize(input.signal.signal.bias))
  );
}

function hasAcceptableSetup(input: TriageArtifactInput): boolean {
  if (!input.setupContext) {
    return true;
  }
  return acceptableSetupLabels.has(normalize(input.setupContext.setup_quality_label));
}

function hasFreshData(input: TriageArtifactInput): boolean {
  return Boolean(input.memory && freshLabels.has(normalize(input.memory.freshness_label)));
}

function hasUsableReadiness(input: TriageArtifactInput): boolean {
  if (!input.readiness) {
    return true;
  }
  return ["ready", "acceptable", "review_recommended"].includes(normalize(input.readiness.assessment.readiness_label));
}

function hasSevereRisk(input: TriageArtifactInput): boolean {
  return input.signal.risk_notes.some((note) => severeRiskSeverities.has(normalize(note.severity)));
}

function hasCriticalQualityFinding(input: TriageArtifactInput): boolean {
  return input.quality?.findings.some((finding) => criticalSeverities.has(normalize(finding.severity))) === true;
}

function hasMixedTimeframeContext(input: TriageArtifactInput): boolean {
  const agreement = input.setupContext?.timeframe_agreement_json;
  if (!agreement) {
    return false;
  }
  return Object.values(agreement).some((value) => {
    if (typeof value !== "string") {
      return false;
    }
    const normalized = normalize(value);
    return normalized.includes("mixed") || normalized.includes("unknown") || normalized.includes("conflict");
  });
}

function hasEvidenceConflict(direction: string, bias: string): boolean {
  const normalizedDirection = normalize(direction);
  const normalizedBias = normalize(bias);
  return (
    (normalizedBias === "bullish" && normalizedDirection === "bearish") ||
    (normalizedBias === "bearish" && normalizedDirection === "bullish") ||
    normalizedDirection.includes("conflict")
  );
}

function hasReportConflict(input: TriageArtifactInput): boolean {
  const text = JSON.stringify(input.report?.sections || {}).toLowerCase();
  return text.includes("conflict") || text.includes("disagreement") || text.includes("grounding issue");
}

function hasScreenshotReviewNeed(input: TriageArtifactInput): boolean {
  const text = JSON.stringify(input.report?.sections || {}).toLowerCase();
  return text.includes("low-confidence") || text.includes("requires human review") || text.includes("review_required");
}

function avoidReason(input: TriageArtifactInput): TriageReason {
  if (normalize(input.signal.signal.classification_status) === "no_signal") {
    return reason("No directional signal");
  }
  return reason("Avoid condition");
}

function warningText(value: Record<string, unknown>): string {
  return Object.values(value)
    .filter((item) => typeof item === "string")
    .join(" ")
    .toLowerCase();
}

function normalize(value: string | null | undefined): string {
  return value?.trim().toLowerCase() || "";
}

function dedupeReasons(reasons: TriageReason[]): TriageReason[] {
  const seen = new Set<string>();
  return reasons.filter((item) => {
    if (seen.has(item.label)) {
      return false;
    }
    seen.add(item.label);
    return true;
  });
}
