import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import OperationsMiddleware
from app.core.rate_limit import create_rate_limiter
from app.modules.action_plans.routes import router as action_plans_router
from app.modules.advanced_features.routes import router as advanced_features_router
from app.modules.ai_intelligence.routes import router as ai_intelligence_router
from app.modules.analysis.routes import router as analysis_router
from app.modules.artifact_graph.routes import router as artifact_graph_router
from app.modules.audit_timeline.routes import router as audit_timeline_router
from app.modules.backfill_plans.routes import router as backfill_plans_router
from app.modules.backtest_experiments.routes import router as backtest_experiments_router
from app.modules.candle_gap_recovery.routes import router as candle_gap_recovery_router
from app.modules.candles.routes import router as candles_router
from app.modules.capabilities.routes import router as capabilities_router
from app.modules.chart_screenshots.routes import router as chart_screenshot_router
from app.modules.cohort_drift.routes import router as cohort_drift_router
from app.modules.confidence_calibration.routes import router as confidence_calibration_router
from app.modules.context_packs.routes import router as context_packs_router
from app.modules.cross_asset_context.routes import router as cross_asset_context_router
from app.modules.data_contracts.routes import router as data_contracts_router
from app.modules.data_quality.routes import router as data_quality_router
from app.modules.data_retention.routes import router as data_retention_router
from app.modules.data_sources.routes import router as data_sources_router
from app.modules.decision_readiness.routes import router as decision_readiness_router
from app.modules.engine_executions.routes import router as engine_executions_router
from app.modules.engine_versions.routes import router as engine_versions_router
from app.modules.event_studies.routes import router as event_studies_router
from app.modules.explanation_comparison.routes import router as explanation_comparison_router
from app.modules.explanations.routes import router as explanations_router
from app.modules.historical_cases.routes import router as historical_cases_router
from app.modules.imports.routes import router as imports_router
from app.modules.intelligence_catalog.routes import router as intelligence_catalog_router
from app.modules.intelligence_datasets.routes import router as intelligence_datasets_router
from app.modules.intelligence_metrics.routes import router as intelligence_metrics_router
from app.modules.intelligence_quality.routes import router as intelligence_quality_router
from app.modules.intelligence_reports.routes import router as intelligence_reports_router
from app.modules.live.routes import router as live_router
from app.modules.llm_explanations.routes import router as llm_explanations_router
from app.modules.market_memory.routes import router as market_memory_router
from app.modules.market_regimes.routes import router as market_regimes_router
from app.modules.market_scans.routes import router as market_scans_router
from app.modules.market_sessions.routes import router as market_sessions_router
from app.modules.news.routes import news_events_router
from app.modules.news.routes import router as news_router
from app.modules.notifications.routes import router as notifications_router
from app.modules.operator_playbooks.routes import router as operator_playbooks_router
from app.modules.operator_reviews.routes import router as operator_reviews_router
from app.modules.outcomes.routes import router as outcomes_router
from app.modules.pattern_attribution.routes import router as pattern_attribution_router
from app.modules.preference_profiles.routes import router as preference_profiles_router
from app.modules.profile_diagnostics.routes import router as profile_diagnostics_router
from app.modules.profile_governance.routes import router as profile_governance_router
from app.modules.profile_simulations.routes import router as profile_simulations_router
from app.modules.provider_health.routes import router as provider_health_router
from app.modules.provider_polling.routes import router as provider_polling_router
from app.modules.reasoning.routes import router as reasoning_router
from app.modules.rule_packs.routes import router as rule_packs_router
from app.modules.scenario_ensembles.routes import router as scenario_ensembles_router
from app.modules.scenario_outcomes.routes import router as scenario_outcomes_router
from app.modules.setup_context.routes import router as setup_context_router
from app.modules.signal_digests.routes import router as signal_digests_router
from app.modules.signal_priority.routes import router as signal_priority_router
from app.modules.signals.routes import router as signals_router
from app.modules.state_machines.routes import router as state_machines_router
from app.modules.strategy_profiles.routes import router as strategy_profiles_router
from app.modules.symbols.routes import router as symbols_router
from app.modules.synthetic_fixtures.routes import router as synthetic_fixtures_router
from app.modules.timeframe_aggregation.routes import router as timeframe_aggregation_router
from app.modules.trading_journal.routes import router as trading_journal_router
from app.modules.users.routes import router as users_router
from app.modules.walk_forward_validation.routes import router as walk_forward_validation_router
from app.modules.webhook_outbox.routes import router as webhook_outbox_router
from app.modules.workspaces.routes import router as workspaces_router
from app.routes.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = app.state.settings
    configure_logging(settings.log_level)
    app.state.logger = logging.getLogger(settings.service_name)
    app.state.logger.info(
        "app_startup",
        extra={"app_env": settings.app_env.value, "service": settings.service_name},
    )
    yield
    app.state.logger.info(
        "app_shutdown",
        extra={"app_env": settings.app_env.value, "service": settings.service_name},
    )
    await app.state.rate_limiter.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title=resolved_settings.service_title,
        version=resolved_settings.service_version,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.logger = logging.getLogger(resolved_settings.service_name)
    app.state.rate_limiter = create_rate_limiter(resolved_settings)
    if resolved_settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved_settings.cors_allowed_origins,
            allow_credentials=resolved_settings.cors_allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(
        OperationsMiddleware,
        settings=resolved_settings,
        rate_limiter=app.state.rate_limiter,
    )
    register_error_handlers(app)
    routers = (
        health_router,
        workspaces_router,
        users_router,
        symbols_router,
        data_sources_router,
        capabilities_router,
        engine_versions_router,
        imports_router,
        provider_polling_router,
        provider_health_router,
        live_router,
        candles_router,
        data_quality_router,
        candle_gap_recovery_router,
        analysis_router,
        advanced_features_router,
        market_regimes_router,
        market_sessions_router,
        timeframe_aggregation_router,
        cross_asset_context_router,
        strategy_profiles_router,
        signals_router,
        signal_digests_router,
        signal_priority_router,
        outcomes_router,
        setup_context_router,
        trading_journal_router,
        market_memory_router,
        cohort_drift_router,
        pattern_attribution_router,
        preference_profiles_router,
        confidence_calibration_router,
        profile_diagnostics_router,
        backtest_experiments_router,
        walk_forward_validation_router,
        reasoning_router,
        scenario_ensembles_router,
        scenario_outcomes_router,
        action_plans_router,
        context_packs_router,
        explanations_router,
        explanation_comparison_router,
        llm_explanations_router,
        news_events_router,
        news_router,
        event_studies_router,
        rule_packs_router,
        intelligence_reports_router,
        intelligence_metrics_router,
        intelligence_catalog_router,
        intelligence_datasets_router,
        intelligence_quality_router,
        ai_intelligence_router,
        audit_timeline_router,
        chart_screenshot_router,
        notifications_router,
        operator_reviews_router,
        operator_playbooks_router,
        profile_governance_router,
        profile_simulations_router,
        market_scans_router,
        synthetic_fixtures_router,
        webhook_outbox_router,
        artifact_graph_router,
        state_machines_router,
        backfill_plans_router,
        data_contracts_router,
        data_retention_router,
        decision_readiness_router,
        engine_executions_router,
    )
    for router in routers:
        app.include_router(router, prefix=resolved_settings.api_prefix)
    return app


app = create_app()
