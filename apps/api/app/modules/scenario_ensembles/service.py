from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.reasoning.models import ReasoningRunStatus
from app.modules.reasoning.repository import ScenarioReasoningRepository
from app.modules.reasoning.service import ScenarioReasoningService
from app.modules.scenario_ensembles.consensus import (
    EnsembleProviderOutput,
    build_provider_output,
    compute_consensus,
)
from app.modules.scenario_ensembles.models import (
    ScenarioConsensusLabel,
    ScenarioConsensusResult,
    ScenarioEnsembleItem,
    ScenarioEnsembleRun,
    ScenarioEnsembleRunStatus,
)
from app.modules.scenario_ensembles.repository import ScenarioEnsembleRepository
from app.modules.scenario_ensembles.schemas import (
    ScenarioConsensusResultRead,
    ScenarioEnsembleItemRead,
    ScenarioEnsembleProviderRequest,
    ScenarioEnsembleResponse,
    ScenarioEnsembleRunRead,
)
from app.modules.signals.models import Signal
from app.modules.signals.repository import SignalRepository


class ScenarioEnsembleService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = ScenarioEnsembleRepository(session)
        self.signal_repository = SignalRepository(session)
        self.reasoning_service = ScenarioReasoningService(session, settings=self.settings)
        self.reasoning_repository = ScenarioReasoningRepository(session)

    async def run_signal_ensemble(
        self,
        signal_id: UUID,
        providers: list[ScenarioEnsembleProviderRequest],
        force_recompute: bool = False,
    ) -> ScenarioEnsembleResponse:
        try:
            signal = await self.load_signal(signal_id)
            provider_models = self.normalize_provider_models(providers)
            requested_providers = [item.provider for item in provider_models]
            requested_models = [item.model for item in provider_models]
            if not force_recompute:
                existing = await self.repository.get_latest_completed_for_request(
                    signal_id=signal.id,
                    ensemble_version=self.settings.scenario_ensemble_version,
                    providers=requested_providers,
                    models=requested_models,
                )
                if existing is not None:
                    return await self.response_for_run(existing)
            run = await self.repository.create_run(
                ScenarioEnsembleRun(
                    id=uuid4(),
                    workspace_id=signal.workspace_id,
                    signal_id=signal.id,
                    analysis_run_id=signal.analysis_run_id,
                    status=ScenarioEnsembleRunStatus.PENDING.value,
                    ensemble_version=self.settings.scenario_ensemble_version,
                    requested_providers_json=requested_providers,
                    requested_models_json=requested_models,
                    reasoning_run_ids_json=[],
                    consensus_score=Decimal("0.0000"),
                    consensus_label=ScenarioConsensusLabel.FAILED.value,
                    summary="Scenario ensemble run is pending.",
                    safety_status="not_checked",
                    grounding_status="not_checked",
                    metadata_json={
                        "providerModelCount": len(provider_models),
                        "forceRecompute": force_recompute,
                    },
                )
            )
            outputs: list[EnsembleProviderOutput] = []
            reasoning_run_ids: list[str] = []
            for provider_model in provider_models:
                response = await self.reasoning_service.generate_signal_scenarios(
                    signal_id=signal.id,
                    provider=provider_model.provider,
                    model=provider_model.model,
                    force_recompute=force_recompute,
                )
                reasoning_run = response.reasoning_run
                reasoning_run_ids.append(str(reasoning_run.id))
                scenarios = await self.reasoning_repository.list_scenarios(reasoning_run.id)
                output = build_provider_output(
                    provider=provider_model.provider,
                    model=provider_model.model,
                    status=reasoning_run.status.value,
                    safety_status=reasoning_run.safety_status.value,
                    grounding_status=reasoning_run.grounding_status.value,
                    scenarios=scenarios,
                )
                outputs.append(output)
                await self.repository.create_item(
                    ScenarioEnsembleItem(
                        id=uuid4(),
                        workspace_id=signal.workspace_id,
                        ensemble_run_id=run.id,
                        reasoning_run_id=reasoning_run.id,
                        provider=provider_model.provider,
                        model=provider_model.model,
                        status=reasoning_run.status.value,
                        scenario_types_json=[scenario.scenario_type for scenario in scenarios],
                        suggested_actions_json=sorted(
                            {
                                action
                                for scenario in scenarios
                                for action in scenario.suggested_backend_actions_json
                            }
                        ),
                        safety_status=reasoning_run.safety_status.value,
                        grounding_status=reasoning_run.grounding_status.value,
                        summary=response.summary,
                        error_message=reasoning_run.error_message,
                    )
                )
            consensus = compute_consensus(
                outputs,
                min_agreement_ratio=self.settings.scenario_ensemble_min_agreement_ratio,
            )
            run.reasoning_run_ids_json = reasoning_run_ids
            run.consensus_score = consensus.consensus_score
            run.consensus_label = consensus.consensus_label.value
            run.summary = consensus.summary
            run.safety_status = consensus.safety_status
            run.grounding_status = consensus.grounding_status
            run.error_message = None
            run.metadata_json = {**run.metadata_json, **consensus.metadata}
            run.status = run_status_for(consensus.consensus_label, outputs)
            await self.repository.replace_consensus_results(
                run.id,
                [
                    ScenarioConsensusResult(
                        id=uuid4(),
                        workspace_id=signal.workspace_id,
                        ensemble_run_id=run.id,
                        scenario_type=result.scenario_type,
                        agreement_count=result.agreement_count,
                        disagreement_count=result.disagreement_count,
                        possibility_labels_json=result.possibility_labels,
                        supporting_evidence_json=result.supporting_evidence,
                        conflicting_evidence_json=result.conflicting_evidence,
                        consensus_label=result.consensus_label.value,
                        metadata_json=result.metadata,
                    )
                    for result in consensus.results
                ],
            )
            await self.repository.update_run(run)
            await self.session.commit()
            return await self.response_for_run(run)
        except Exception:
            await self.session.rollback()
            raise

    async def list_signal_runs(self, signal_id: UUID) -> list[ScenarioEnsembleRunRead]:
        signal = await self.load_signal(signal_id)
        runs = await self.repository.list_signal_runs(signal.id)
        return [ScenarioEnsembleRunRead.model_validate(run) for run in runs]

    async def get_run(self, ensemble_run_id: UUID) -> ScenarioEnsembleResponse:
        run = await self.load_run(ensemble_run_id)
        return await self.response_for_run(run)

    async def list_items(self, ensemble_run_id: UUID) -> list[ScenarioEnsembleItemRead]:
        await self.load_run(ensemble_run_id)
        items = await self.repository.list_items(ensemble_run_id)
        return [ScenarioEnsembleItemRead.model_validate(item) for item in items]

    async def list_consensus(
        self,
        ensemble_run_id: UUID,
    ) -> list[ScenarioConsensusResultRead]:
        await self.load_run(ensemble_run_id)
        results = await self.repository.list_consensus_results(ensemble_run_id)
        return [ScenarioConsensusResultRead.model_validate(result) for result in results]

    async def response_for_run(self, run: ScenarioEnsembleRun) -> ScenarioEnsembleResponse:
        items = await self.repository.list_items(run.id)
        consensus = await self.repository.list_consensus_results(run.id)
        return ScenarioEnsembleResponse(
            run=ScenarioEnsembleRunRead.model_validate(run),
            items=[ScenarioEnsembleItemRead.model_validate(item) for item in items],
            consensus=[ScenarioConsensusResultRead.model_validate(result) for result in consensus],
        )

    async def load_signal(self, signal_id: UUID) -> Signal:
        signal = await self.signal_repository.get_by_id(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return signal

    async def load_run(self, ensemble_run_id: UUID) -> ScenarioEnsembleRun:
        run = await self.repository.get_run(ensemble_run_id)
        if run is None:
            raise AppError(
                404,
                "scenario_ensemble_run_not_found",
                "Scenario ensemble run not found",
            )
        return run

    def normalize_provider_models(
        self,
        providers: list[ScenarioEnsembleProviderRequest],
    ) -> list[ScenarioEnsembleProviderRequest]:
        if not providers:
            return [
                ScenarioEnsembleProviderRequest(
                    provider=self.settings.scenario_ensemble_default_provider,
                    model=self.settings.llm_default_model,
                )
            ]
        max_providers = self.settings.scenario_ensemble_max_providers
        if len(providers) > max_providers:
            raise AppError(
                422,
                "scenario_ensemble_provider_limit_exceeded",
                f"Scenario ensemble supports at most {max_providers} provider/model requests",
            )
        return providers


def run_status_for(
    consensus_label: ScenarioConsensusLabel,
    outputs: list[EnsembleProviderOutput],
) -> str:
    if consensus_label == ScenarioConsensusLabel.FAILED:
        return ScenarioEnsembleRunStatus.FAILED.value
    if outputs and all(
        output.status == ReasoningRunStatus.PROVIDER_NOT_CONFIGURED.value for output in outputs
    ):
        return ScenarioEnsembleRunStatus.PROVIDER_NOT_CONFIGURED.value
    if outputs and any(output.status != ReasoningRunStatus.COMPLETED.value for output in outputs):
        return ScenarioEnsembleRunStatus.COMPLETED_WITH_WARNINGS.value
    return ScenarioEnsembleRunStatus.COMPLETED.value
