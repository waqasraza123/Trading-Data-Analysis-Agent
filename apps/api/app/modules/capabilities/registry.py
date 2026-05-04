from dataclasses import dataclass, field

from app.modules.capabilities.models import (
    CapabilityCategory,
    CapabilityExecutionType,
    CapabilitySafetyLevel,
    CapabilityStatus,
)


DEFAULT_CAPABILITY_VERSION = "v1"


@dataclass(frozen=True)
class CapabilityDefinition:
    key: str
    name: str
    category: CapabilityCategory
    execution_type: CapabilityExecutionType
    safety_level: CapabilitySafetyLevel
    module_path: str | None
    status: CapabilityStatus = CapabilityStatus.AVAILABLE
    requires_external_credentials: bool = False
    requires_database: bool = True
    input_contracts: tuple[str, ...] = ()
    output_contracts: tuple[str, ...] = ()
    produced_artifacts: tuple[str, ...] = ()
    route_refs: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
    version: str = DEFAULT_CAPABILITY_VERSION


def contract_refs(keys: tuple[str, ...]) -> list[dict[str, object]]:
    return [{"key": key, "version": "v1"} for key in keys]


def artifact_refs(keys: tuple[str, ...]) -> list[dict[str, object]]:
    return [{"artifact": key} for key in keys]


def route_refs(paths: tuple[str, ...]) -> list[dict[str, object]]:
    return [{"path": path} for path in paths]


def dependency_refs(keys: tuple[str, ...]) -> list[dict[str, object]]:
    return [{"capabilityKey": key} for key in keys]


def metadata(
    *,
    deterministic: bool,
    read_only: bool,
    produces_financial_advice: bool = False,
    executes_broker_actions: bool = False,
    mutates_intelligence_artifacts: bool = False,
    safe_to_run_automatically: bool = False,
    module_setting: str | None = None,
    credential_settings: tuple[str, ...] = (),
    notes: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "deterministic": deterministic,
        "readOnly": read_only,
        "producesFinancialAdvice": produces_financial_advice,
        "executesBrokerActions": executes_broker_actions,
        "mutatesIntelligenceArtifacts": mutates_intelligence_artifacts,
        "safeToRunAutomatically": safe_to_run_automatically,
    }
    if module_setting is not None:
        payload["moduleSetting"] = module_setting
    if credential_settings:
        payload["credentialSettings"] = list(credential_settings)
    if notes is not None:
        payload["notes"] = notes
    return payload


DEFAULT_CAPABILITIES: tuple[CapabilityDefinition, ...] = (
    CapabilityDefinition(
        key="candle_imports",
        name="Historical Candle Imports",
        category=CapabilityCategory.INGESTION,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.imports",
        input_contracts=("candle_import_row",),
        output_contracts=("normalized_candle",),
        produced_artifacts=("import_batches", "import_errors", "candles"),
        route_refs=("/imports/csv", "/imports/json", "/imports/{import_batch_id}/errors"),
        dependencies=("datasets",),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            safe_to_run_automatically=False,
            notes="Stores normalized candle data through the shared candle path.",
        ),
    ),
    CapabilityDefinition(
        key="live_feed_ingestion",
        name="Live Feed Ingestion",
        category=CapabilityCategory.INGESTION,
        execution_type=CapabilityExecutionType.EXTERNAL_PROVIDER,
        safety_level=CapabilitySafetyLevel.PROVIDER_BACKED,
        module_path="app.modules.live",
        requires_external_credentials=True,
        input_contracts=("webhook_payload",),
        output_contracts=("normalized_candle",),
        produced_artifacts=("live_feed_subscriptions", "live_feed_events", "candles"),
        route_refs=("/live/subscriptions", "/live/events"),
        dependencies=("datasets",),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            module_setting="live_feed_provider",
            credential_settings=("live_feed_api_key",),
            notes="Availability depends on configured provider credentials.",
        ),
    ),
    CapabilityDefinition(
        key="provider_polling",
        name="Market Data Provider Polling",
        category=CapabilityCategory.INGESTION,
        execution_type=CapabilityExecutionType.EXTERNAL_PROVIDER,
        safety_level=CapabilitySafetyLevel.PROVIDER_BACKED,
        module_path="app.modules.provider_polling",
        input_contracts=("normalized_candle",),
        output_contracts=("normalized_candle",),
        produced_artifacts=("provider_polling_requests", "provider_polling_errors", "candles"),
        route_refs=("/provider-polling/requests",),
        dependencies=("datasets",),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            safe_to_run_automatically=False,
            notes="Uses configured provider adapters; public Binance polling does not require a key.",
        ),
    ),
    CapabilityDefinition(
        key="analysis_lifecycle",
        name="Analysis Run Lifecycle",
        category=CapabilityCategory.ANALYSIS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.analysis",
        input_contracts=("normalized_candle",),
        output_contracts=("feature_snapshot", "indicator_snapshot"),
        produced_artifacts=("analysis_runs", "analysis_audit_logs", "feature_snapshots", "indicator_snapshots", "pattern_candidates", "signals"),
        route_refs=("/analysis-runs", "/analysis-runs/{analysis_run_id}/retry"),
        dependencies=("candle_imports", "live_feed_ingestion", "provider_polling"),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
    CapabilityDefinition(
        key="signal_classification",
        name="Deterministic Signal Classification",
        category=CapabilityCategory.SIGNAL,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.signals",
        input_contracts=("feature_snapshot", "indicator_snapshot", "strategy_profile_config"),
        output_contracts=("signal_snapshot",),
        produced_artifacts=("signals", "signal_confidence_components", "signal_evidence", "signal_risk_notes"),
        route_refs=("/analysis-runs/{analysis_run_id}/signal", "/signals/{signal_id}"),
        dependencies=("analysis_lifecycle", "rule_packs"),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
    CapabilityDefinition(
        key="deterministic_explanations",
        name="Deterministic Explanations",
        category=CapabilityCategory.EXPLANATION,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.explanations",
        input_contracts=("signal_snapshot",),
        produced_artifacts=("deterministic_explanations",),
        route_refs=("/signals/{signal_id}/explanation", "/analysis-runs/{analysis_run_id}/explanation"),
        dependencies=("signal_classification", "safety_policies"),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
    CapabilityDefinition(
        key="news_correlation",
        name="News Correlation",
        category=CapabilityCategory.ANALYSIS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.news",
        output_contracts=("signal_snapshot",),
        produced_artifacts=("news_events", "signal_news_correlations"),
        route_refs=("/news-events", "/signals/{signal_id}/news-correlations"),
        dependencies=("signal_classification",),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            notes="Adds contextual correlation only and does not claim causation.",
        ),
    ),
    CapabilityDefinition(
        key="llm_explanations",
        name="Grounded LLM Explanations",
        category=CapabilityCategory.EXPLANATION,
        execution_type=CapabilityExecutionType.LLM_PROVIDER,
        safety_level=CapabilitySafetyLevel.REVIEW_REQUIRED,
        module_path="app.modules.llm_explanations",
        status=CapabilityStatus.EXPERIMENTAL,
        requires_external_credentials=True,
        input_contracts=("signal_snapshot",),
        produced_artifacts=("llm_explanations",),
        route_refs=("/signals/{signal_id}/ai-explanation", "/analysis-runs/{analysis_run_id}/ai-explanation"),
        dependencies=("deterministic_explanations", "safety_policies"),
        metadata=metadata(
            deterministic=False,
            read_only=False,
            mutates_intelligence_artifacts=True,
            module_setting="llm_explanations_enabled",
            credential_settings=("openai_api_key", "anthropic_api_key"),
        ),
    ),
    CapabilityDefinition(
        key="scenario_reasoning",
        name="Scenario Reasoning",
        category=CapabilityCategory.REASONING,
        execution_type=CapabilityExecutionType.LLM_PROVIDER,
        safety_level=CapabilitySafetyLevel.REVIEW_REQUIRED,
        module_path="app.modules.reasoning",
        status=CapabilityStatus.EXPERIMENTAL,
        requires_external_credentials=True,
        input_contracts=("signal_snapshot", "reasoning_output"),
        output_contracts=("reasoning_output", "scenario_hypothesis"),
        produced_artifacts=("llm_reasoning_runs", "scenario_hypotheses"),
        route_refs=("/signals/{signal_id}/reasoning", "/reasoning-runs/{reasoning_run_id}"),
        dependencies=("signal_classification", "historical_cases", "safety_policies"),
        metadata=metadata(
            deterministic=False,
            read_only=False,
            mutates_intelligence_artifacts=True,
            module_setting="llm_reasoning_enabled",
            credential_settings=("openai_api_key", "anthropic_api_key"),
        ),
    ),
    CapabilityDefinition(
        key="action_plans",
        name="Reasoning Action Plans",
        category=CapabilityCategory.OPERATIONS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.REVIEW_REQUIRED,
        module_path="app.modules.action_plans",
        produced_artifacts=("reasoning_action_plans", "reasoning_action_items"),
        route_refs=("/reasoning-runs/{reasoning_run_id}/action-plan", "/reasoning-action-plans/{action_plan_id}"),
        dependencies=("scenario_reasoning", "safety_policies"),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            notes="Creates backend follow-up items only; no alerts or broker operations.",
        ),
    ),
    CapabilityDefinition(
        key="reasoning_action_worker",
        name="Reasoning Action Worker",
        category=CapabilityCategory.OPERATIONS,
        execution_type=CapabilityExecutionType.WORKER,
        safety_level=CapabilitySafetyLevel.REVIEW_REQUIRED,
        module_path="app.modules.action_plans.worker",
        status=CapabilityStatus.DISABLED,
        produced_artifacts=("reasoning_action_worker_runs",),
        route_refs=("/reasoning-action-items/due", "/reasoning-action-worker/status"),
        dependencies=("action_plans",),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            module_setting="reasoning_action_worker_enabled",
        ),
    ),
    CapabilityDefinition(
        key="outcomes",
        name="Outcome Evaluation",
        category=CapabilityCategory.OUTCOME,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.outcomes",
        produced_artifacts=("signal_outcomes", "outcome_evaluation_runs"),
        route_refs=("/signals/{signal_id}/outcomes", "/outcome-evaluation-runs/{run_id}"),
        dependencies=("signal_classification", "datasets"),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
    CapabilityDefinition(
        key="trading_journal",
        name="Trading Journal Feedback Loop",
        category=CapabilityCategory.OUTCOME,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.REVIEW_REQUIRED,
        module_path="app.modules.trading_journal",
        produced_artifacts=(
            "journal_entries",
            "journal_entry_reviews",
            "journal_entry_attachments",
        ),
        route_refs=(
            "/journal-entries",
            "/journal-entries/{entry_id}/review",
            "/journal-entries/{entry_id}/attachments",
        ),
        dependencies=("signal_classification", "outcomes", "operator_reviews"),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=False,
            safe_to_run_automatically=False,
            notes=(
                "Records user decision notes and deterministic outcome comparisons only; "
                "no broker execution, signal mutation, or financial advice."
            ),
        ),
    ),
    CapabilityDefinition(
        key="scenario_outcomes",
        name="Scenario Hypothesis Outcome Tracking",
        category=CapabilityCategory.OUTCOME,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.scenario_outcomes",
        produced_artifacts=("scenario_hypothesis_outcomes", "scenario_outcome_summary_runs"),
        route_refs=(
            "/reasoning/scenarios/{scenario_hypothesis_id}/outcome",
            "/reasoning/runs/{reasoning_run_id}/scenario-outcomes",
            "/scenario-outcomes/summary",
        ),
        dependencies=("scenario_reasoning", "outcomes", "news_correlation"),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            notes=(
                "Evaluates persisted scenario hypotheses against stored signal outcomes only; "
                "does not call LLMs or mutate source artifacts."
            ),
        ),
    ),
    CapabilityDefinition(
        key="profile_diagnostics",
        name="Profile Diagnostics",
        category=CapabilityCategory.DIAGNOSTICS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.REVIEW_REQUIRED,
        module_path="app.modules.profile_diagnostics",
        produced_artifacts=("strategy_profile_diagnostic_runs", "strategy_profile_diagnostics", "pattern_outcome_diagnostics", "calibration_recommendations"),
        route_refs=("/profile-diagnostics/runs", "/profile-diagnostics/recommendations"),
        dependencies=("outcomes", "strategy_profiles"),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
    CapabilityDefinition(
        key="intelligence_reports",
        name="Intelligence Reports",
        category=CapabilityCategory.REPORTING,
        execution_type=CapabilityExecutionType.READ_ONLY,
        safety_level=CapabilitySafetyLevel.SAFE_READ,
        module_path="app.modules.intelligence_reports",
        produced_artifacts=(),
        route_refs=("/intelligence-reports/signals/{signal_id}", "/intelligence-reports/analysis-runs/{analysis_run_id}"),
        dependencies=("signal_classification", "outcomes", "scenario_reasoning"),
        metadata=metadata(deterministic=True, read_only=True),
    ),
    CapabilityDefinition(
        key="audit_timeline",
        name="Audit Timeline",
        category=CapabilityCategory.REPORTING,
        execution_type=CapabilityExecutionType.READ_ONLY,
        safety_level=CapabilitySafetyLevel.SAFE_READ,
        module_path="app.modules.audit_timeline",
        route_refs=("/audit-timeline/analysis-runs/{analysis_run_id}", "/audit-timeline/signals/{signal_id}"),
        dependencies=("analysis_lifecycle", "signal_classification"),
        metadata=metadata(deterministic=True, read_only=True),
    ),
    CapabilityDefinition(
        key="intelligence_quality",
        name="Intelligence Quality Gates",
        category=CapabilityCategory.DIAGNOSTICS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.REVIEW_REQUIRED,
        module_path="app.modules.intelligence_quality",
        produced_artifacts=("intelligence_quality_runs", "intelligence_quality_findings", "shadow_classification_results"),
        route_refs=("/intelligence-quality/signals/{signal_id}", "/intelligence-quality/runs/{run_id}"),
        dependencies=("signal_classification", "safety_policies"),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
    CapabilityDefinition(
        key="chart_screenshots",
        name="Chart Screenshot Intelligence",
        category=CapabilityCategory.INGESTION,
        execution_type=CapabilityExecutionType.EXTERNAL_PROVIDER,
        safety_level=CapabilitySafetyLevel.REVIEW_REQUIRED,
        module_path="app.modules.chart_screenshots",
        requires_external_credentials=True,
        input_contracts=("chart_axis_calibration", "chart_ocr_metadata"),
        output_contracts=("normalized_candle",),
        produced_artifacts=("chart_screenshot_runs", "candles"),
        route_refs=("/chart-screenshot-runs", "/chart-screenshot-runs/{run_id}/decision"),
        dependencies=("datasets", "safety_policies"),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            module_setting="chart_ocr_enabled",
            credential_settings=("chart_ocr_provider",),
        ),
    ),
    CapabilityDefinition(
        key="market_scans",
        name="Market Scans",
        category=CapabilityCategory.OPERATIONS,
        execution_type=CapabilityExecutionType.WORKER,
        safety_level=CapabilitySafetyLevel.REVIEW_REQUIRED,
        module_path="app.modules.market_scans",
        status=CapabilityStatus.DISABLED,
        produced_artifacts=("market_watchlists", "scheduled_scan_configs", "scheduled_scan_runs", "scheduled_scan_run_items"),
        route_refs=("/market-watchlists", "/scheduled-scan-configs", "/scheduled-scan-runs"),
        dependencies=("analysis_lifecycle",),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            module_setting="market_scan_worker_enabled",
        ),
    ),
    CapabilityDefinition(
        key="historical_cases",
        name="Historical Cases",
        category=CapabilityCategory.ANALYSIS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.historical_cases",
        produced_artifacts=("historical_case_vectors", "historical_case_searches"),
        route_refs=("/signals/{signal_id}/historical-cases", "/analysis-runs/{analysis_run_id}/historical-cases"),
        dependencies=("signal_classification", "outcomes"),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
    CapabilityDefinition(
        key="market_regimes",
        name="Market Regimes",
        category=CapabilityCategory.ANALYSIS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.market_regimes",
        produced_artifacts=("market_regime_contexts",),
        route_refs=("/analysis-runs/{analysis_run_id}/market-regime", "/signals/{signal_id}/market-regime"),
        dependencies=("analysis_lifecycle",),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
    CapabilityDefinition(
        key="market_sessions",
        name="Market Sessions",
        category=CapabilityCategory.ANALYSIS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.market_sessions",
        produced_artifacts=("market_session_contexts",),
        route_refs=("/analysis-runs/{analysis_run_id}/market-session", "/signals/{signal_id}/market-session"),
        dependencies=("analysis_lifecycle",),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
    CapabilityDefinition(
        key="cross_asset_context",
        name="Cross-Asset Context",
        category=CapabilityCategory.ANALYSIS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.cross_asset_context",
        produced_artifacts=("cross_asset_context_runs", "cross_asset_context_results"),
        route_refs=(
            "/analysis-runs/{analysis_run_id}/cross-asset-context",
            "/signals/{signal_id}/cross-asset-context",
            "/cross-asset-context/runs/{run_id}/results",
        ),
        dependencies=("analysis_lifecycle", "signal_classification", "datasets"),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            notes=(
                "Stores contextual correlation, co-movement, divergence, and lead/lag "
                "without claiming causation."
            ),
        ),
    ),
    CapabilityDefinition(
        key="walk_forward_validation",
        name="Walk-Forward Validation",
        category=CapabilityCategory.DIAGNOSTICS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.walk_forward_validation",
        produced_artifacts=(
            "walk_forward_validation_runs",
            "walk_forward_validation_windows",
            "walk_forward_validation_comparisons",
        ),
        route_refs=(
            "/walk-forward-validations/run",
            "/walk-forward-validations/runs",
            "/walk-forward-validations/runs/{run_id}",
        ),
        dependencies=("signal_classification", "outcomes"),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            notes=(
                "Summarizes validation windows and observed follow-through without broker "
                "accounting or strategy mutation."
            ),
        ),
    ),
    CapabilityDefinition(
        key="market_memory",
        name="Rolling Market State Memory",
        category=CapabilityCategory.REPORTING,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.market_memory",
        produced_artifacts=("rolling_market_state_snapshots",),
        route_refs=(
            "/market-memory/snapshots",
            "/market-memory/snapshots/by-symbol",
            "/market-memory/workspaces/{workspace_id}/refresh",
        ),
        dependencies=(
            "datasets",
            "analysis_lifecycle",
            "signal_classification",
            "outcomes",
            "data_quality",
            "market_regimes",
            "market_sessions",
            "cross_asset_context",
        ),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            safe_to_run_automatically=False,
            notes=(
                "Caches latest deterministic context from persisted artifacts only; "
                "does not run analysis or mutate source artifacts."
            ),
        ),
    ),
    CapabilityDefinition(
        key="pattern_attribution",
        name="Pattern Detector Attribution",
        category=CapabilityCategory.DIAGNOSTICS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.pattern_attribution",
        produced_artifacts=("pattern_attribution_runs", "pattern_attribution_results"),
        route_refs=(
            "/pattern-attribution/run",
            "/pattern-attribution/runs",
            "/pattern-attribution/runs/{run_id}/results",
        ),
        dependencies=("analysis_lifecycle", "signal_classification", "outcomes"),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            safe_to_run_automatically=False,
            notes=(
                "Attributes stored pattern candidates against final signals and stored outcomes "
                "without candidate, detector, or signal mutation."
            ),
        ),
    ),
    CapabilityDefinition(
        key="cohort_drift",
        name="Signal Cohort Drift Detection",
        category=CapabilityCategory.DIAGNOSTICS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.cohort_drift",
        produced_artifacts=("cohort_drift_runs", "cohort_drift_results"),
        route_refs=(
            "/cohort-drift/run",
            "/cohort-drift/runs",
            "/cohort-drift/runs/{run_id}/results",
            "/cohort-drift/results/recent",
        ),
        dependencies=("signal_classification", "outcomes", "market_sessions", "market_regimes"),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            notes=(
                "Compares recent stored signal/outcome cohort behavior against a "
                "baseline period without source artifact mutation."
            ),
        ),
    ),
    CapabilityDefinition(
        key="candle_gap_recovery",
        name="Candle Gap Recovery Planner",
        category=CapabilityCategory.OPERATIONS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.candle_gap_recovery",
        produced_artifacts=("candle_gap_recovery_plans", "candle_gap_recovery_items"),
        route_refs=(
            "/candle-gap-recovery/plans",
            "/candle-gap-recovery/plans/{plan_id}/items",
            "/candle-gap-recovery/plans/{plan_id}/prepare-provider-polling",
        ),
        dependencies=("datasets", "provider_polling", "data_quality"),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            safe_to_run_automatically=False,
            notes=(
                "Plans missing final-candle recovery and can create pending polling rows "
                "without executing provider fetches."
            ),
        ),
    ),
    CapabilityDefinition(
        key="explanation_comparison",
        name="Explanation Comparison",
        category=CapabilityCategory.EXPLANATION,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.REVIEW_REQUIRED,
        module_path="app.modules.explanation_comparison",
        status=CapabilityStatus.EXPERIMENTAL,
        produced_artifacts=("explanation_comparison_runs", "explanation_comparison_findings"),
        route_refs=(
            "/signals/{signal_id}/explanation-comparison",
            "/signals/{signal_id}/explanation-comparison/latest",
            "/explanation-comparisons/{run_id}",
        ),
        dependencies=(
            "deterministic_explanations",
            "llm_explanations",
            "scenario_reasoning",
            "news_correlation",
            "safety_policies",
        ),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            notes=(
                "Compares persisted explanation layers and flags alignment issues without "
                "regenerating explanations."
            ),
        ),
    ),
    CapabilityDefinition(
        key="data_quality",
        name="Data Quality",
        category=CapabilityCategory.DIAGNOSTICS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.data_quality",
        produced_artifacts=("data_quality_runs", "data_quality_findings"),
        route_refs=("/data-quality/runs", "/data-quality/findings"),
        dependencies=("datasets",),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
    CapabilityDefinition(
        key="datasets",
        name="Dataset Registry and Exports",
        category=CapabilityCategory.EXPORT,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.REVIEW_REQUIRED,
        module_path="app.modules.intelligence_datasets",
        input_contracts=("dataset_record",),
        produced_artifacts=("intelligence_dataset_exports", "intelligence_dataset_export_items"),
        route_refs=("/intelligence-datasets/exports", "/intelligence-datasets/exports/{export_id}/jsonl"),
        dependencies=("signal_classification", "outcomes", "safety_policies"),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
    CapabilityDefinition(
        key="synthetic_fixtures",
        name="Deterministic Synthetic Candle Fixtures",
        category=CapabilityCategory.OPERATIONS,
        execution_type=CapabilityExecutionType.MANUAL_ONLY,
        safety_level=CapabilitySafetyLevel.RESTRICTED,
        module_path="app.modules.synthetic_fixtures",
        status=CapabilityStatus.EXPERIMENTAL,
        requires_database=False,
        output_contracts=("raw_candle_payload", "csv_candle_fixture", "json_candle_import_payload"),
        route_refs=("/synthetic-fixtures/generate",),
        dependencies=("candle_imports", "data_quality"),
        metadata=metadata(
            deterministic=True,
            read_only=True,
            safe_to_run_automatically=False,
            module_setting="synthetic_fixtures_api_enabled",
            notes=(
                "Generates deterministic development and testing candle fixtures without "
                "external data or persistence."
            ),
        ),
    ),
    CapabilityDefinition(
        key="webhook_outbox",
        name="Webhook Outbox",
        category=CapabilityCategory.OPERATIONS,
        execution_type=CapabilityExecutionType.MANUAL_ONLY,
        safety_level=CapabilitySafetyLevel.RESTRICTED,
        module_path="app.modules.webhook_outbox",
        status=CapabilityStatus.EXPERIMENTAL,
        produced_artifacts=("webhook_subscriptions", "webhook_outbox_events", "webhook_delivery_attempts"),
        route_refs=("/webhook-subscriptions", "/webhook-outbox-events"),
        dependencies=("safety_policies",),
        metadata=metadata(
            deterministic=True,
            read_only=False,
            mutates_intelligence_artifacts=True,
            notes="Stores held backend events only; this registry does not enable delivery.",
        ),
    ),
    CapabilityDefinition(
        key="safety_policies",
        name="Safety Policies",
        category=CapabilityCategory.SAFETY,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.safety_policies",
        produced_artifacts=("safety_policy_sets", "safety_policy_evaluations"),
        route_refs=("/safety-policies",),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
    CapabilityDefinition(
        key="decision_readiness",
        name="Decision Readiness",
        category=CapabilityCategory.DIAGNOSTICS,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.REVIEW_REQUIRED,
        module_path="app.modules.decision_readiness",
        produced_artifacts=("decision_readiness_assessments",),
        route_refs=("/decision-readiness/signals/{signal_id}", "/decision-readiness/analysis-runs/{analysis_run_id}"),
        dependencies=("signal_classification", "intelligence_quality", "safety_policies"),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
    CapabilityDefinition(
        key="rule_packs",
        name="Rule Packs and Reproducibility Manifests",
        category=CapabilityCategory.GOVERNANCE,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.rule_packs",
        produced_artifacts=("rule_packs", "analysis_reproducibility_manifests"),
        route_refs=("/rule-packs", "/analysis-runs/{analysis_run_id}/reproducibility-manifest"),
        dependencies=("engine_versions",),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
    CapabilityDefinition(
        key="state_machines",
        name="State Machine Registry",
        category=CapabilityCategory.GOVERNANCE,
        execution_type=CapabilityExecutionType.DETERMINISTIC_WRITE,
        safety_level=CapabilitySafetyLevel.SAFE_BACKEND_WRITE,
        module_path="app.modules.state_machines",
        produced_artifacts=("state_machine_definitions", "state_transition_validations"),
        route_refs=("/state-machines", "/state-machines/validate-transition"),
        metadata=metadata(deterministic=True, read_only=False, mutates_intelligence_artifacts=True),
    ),
)


DEFAULT_CAPABILITIES_BY_KEY = {definition.key: definition for definition in DEFAULT_CAPABILITIES}
