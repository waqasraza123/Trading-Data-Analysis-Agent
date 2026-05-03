from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.data_contracts.models import DataContract, DataContractValidation
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.live.models import LiveFeedEvent
from app.modules.news.models import SignalNewsCorrelation
from app.modules.outcomes.models import SignalOutcome
from app.modules.patterns.models import PatternCandidate
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.signals.models import Signal
from app.modules.strategy_profiles.models import StrategyProfile


class DataContractRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_contract(self, contract: DataContract) -> DataContract:
        self.session.add(contract)
        await self.session.flush()
        await self.session.refresh(contract)
        return contract

    async def get_contract(self, key: str, version: str) -> DataContract | None:
        statement = select(DataContract).where(
            DataContract.key == key,
            DataContract.version == version,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_contracts(
        self,
        status: str | None = None,
    ) -> list[DataContract]:
        statement: Select[tuple[DataContract]] = select(DataContract)
        if status is not None:
            statement = statement.where(DataContract.status == status)
        statement = statement.order_by(
            DataContract.key.asc(),
            DataContract.version.asc(),
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_validation(
        self,
        validation: DataContractValidation,
    ) -> DataContractValidation:
        self.session.add(validation)
        await self.session.flush()
        await self.session.refresh(validation)
        return validation

    async def list_validations(
        self,
        workspace_id: UUID | None = None,
        contract_key: str | None = None,
        contract_version: str | None = None,
        source_type: str | None = None,
        source_id: UUID | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[DataContractValidation]:
        statement: Select[tuple[DataContractValidation]] = select(DataContractValidation)
        if workspace_id is not None:
            statement = statement.where(DataContractValidation.workspace_id == workspace_id)
        if contract_key is not None:
            statement = statement.where(DataContractValidation.contract_key == contract_key)
        if contract_version is not None:
            statement = statement.where(DataContractValidation.contract_version == contract_version)
        if source_type is not None:
            statement = statement.where(DataContractValidation.source_type == source_type)
        if source_id is not None:
            statement = statement.where(DataContractValidation.source_id == source_id)
        if status is not None:
            statement = statement.where(DataContractValidation.status == status)
        statement = statement.order_by(DataContractValidation.created_at.desc()).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_source_payload(
        self,
        source_type: str,
        source_id: UUID,
    ) -> tuple[UUID | None, dict[str, Any] | list[Any]] | None:
        if source_type == "feature_snapshot":
            snapshot = await self.session.get(FeatureSnapshot, source_id)
            return (snapshot.workspace_id, snapshot.features_json) if snapshot is not None else None
        if source_type == "indicator_snapshot":
            snapshot = await self.session.get(IndicatorSnapshot, source_id)
            return (snapshot.workspace_id, snapshot.indicators_json) if snapshot is not None else None
        if source_type == "pattern_evidence":
            candidate = await self.session.get(PatternCandidate, source_id)
            return (candidate.workspace_id, candidate.evidence_json) if candidate is not None else None
        if source_type == "pattern_metrics":
            candidate = await self.session.get(PatternCandidate, source_id)
            return (candidate.workspace_id, candidate.metrics_json) if candidate is not None else None
        if source_type == "strategy_profile_config":
            profile = await self.session.get(StrategyProfile, source_id)
            if profile is None:
                return None
            return (
                None,
                {
                    "key": profile.key,
                    "version": profile.version,
                    "allowedPatterns": profile.allowed_patterns_json,
                    "excludedPatterns": profile.excluded_patterns_json,
                    "minimumCandidateStrength": str(profile.minimum_candidate_strength),
                    "minimumConfidence": str(profile.minimum_confidence),
                    "componentWeights": profile.component_weights_json,
                    "riskFilters": profile.risk_filters_json,
                    "noSignalRules": profile.no_signal_rules_json,
                },
            )
        if source_type == "signal_snapshot":
            signal = await self.session.get(Signal, source_id)
            if signal is None:
                return None
            return (
                signal.workspace_id,
                {
                    "signalId": str(signal.id),
                    "analysisRunId": str(signal.analysis_run_id),
                    "bias": signal.bias,
                    "classificationStatus": signal.classification_status,
                    "confidenceScore": str(signal.confidence_score),
                    "confidenceLabel": signal.confidence_label,
                    "strategyProfile": signal.strategy_profile_snapshot_json or {},
                    "summary": signal.summary,
                },
            )
        if source_type == "news_correlation_metadata":
            correlation = await self.session.get(SignalNewsCorrelation, source_id)
            return (correlation.workspace_id, correlation.metadata_json) if correlation is not None else None
        if source_type == "outcome_metadata":
            outcome = await self.session.get(SignalOutcome, source_id)
            return (outcome.workspace_id, outcome.metadata_json) if outcome is not None else None
        if source_type == "reasoning_input":
            reasoning_run = await self.session.get(LlmReasoningRun, source_id)
            return (
                (reasoning_run.workspace_id, reasoning_run.input_snapshot_json)
                if reasoning_run is not None
                else None
            )
        if source_type == "reasoning_output":
            reasoning_run = await self.session.get(LlmReasoningRun, source_id)
            if reasoning_run is None or reasoning_run.output_json is None:
                return None
            return (reasoning_run.workspace_id, reasoning_run.output_json)
        if source_type == "scenario_hypothesis":
            scenario = await self.session.get(ScenarioHypothesis, source_id)
            if scenario is None:
                return None
            return (
                scenario.workspace_id,
                {
                    "scenarioType": scenario.scenario_type,
                    "scenarioLabel": scenario.scenario_label,
                    "possibilityLabel": scenario.possibility_label,
                    "supportingEvidence": scenario.supporting_evidence_json,
                    "conflictingEvidence": scenario.conflicting_evidence_json,
                    "outcomeHistory": scenario.outcome_history_json or {},
                    "nextObservations": scenario.next_observations_json,
                    "suggestedBackendActions": scenario.suggested_backend_actions_json,
                    "riskNotes": scenario.risk_notes_json,
                },
            )
        if source_type in {"webhook_payload", "live_feed_event_payload"}:
            event = await self.session.get(LiveFeedEvent, source_id)
            return (event.workspace_id, event.payload_json) if event is not None else None
        if source_type == "chart_axis_calibration":
            run = await self.session.get(ChartScreenshotRun, source_id)
            if run is None or run.axis_calibration_json is None:
                return None
            return (run.workspace_id, run.axis_calibration_json)
        if source_type == "chart_ocr_metadata":
            run = await self.session.get(ChartScreenshotRun, source_id)
            if run is None:
                return None
            ocr_json = run.parser_metadata_json.get("ocr")
            if not isinstance(ocr_json, dict):
                return None
            return (run.workspace_id, ocr_json)
        return None
