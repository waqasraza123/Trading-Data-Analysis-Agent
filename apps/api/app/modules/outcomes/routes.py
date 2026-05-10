from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.outcomes.schemas import (
    AnalysisRunOutcomeEvaluationRead,
    OutcomeBackfillRequest,
    OutcomeEvaluationRequest,
    OutcomeEvaluationRunRead,
    OutcomePerformanceQuery,
    OutcomePerformanceRead,
    SignalOutcomeEvaluationRead,
    SignalOutcomeRead,
)
from app.modules.outcomes.service import OutcomeEvaluationService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(tags=["outcomes"])


def get_outcome_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> OutcomeEvaluationService:
    return OutcomeEvaluationService(session)


@router.post(
    "/signals/{signal_id}/outcomes/evaluate",
    response_model=SignalOutcomeEvaluationRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def evaluate_signal_outcomes(
    signal_id: UUID,
    payload: OutcomeEvaluationRequest,
    service: Annotated[OutcomeEvaluationService, Depends(get_outcome_service)],
) -> SignalOutcomeEvaluationRead:
    outcomes = await service.evaluate_signal_outcomes(
        signal_id=signal_id,
        horizons_minutes=payload.horizons_minutes,
        force_recompute=payload.force_recompute,
    )
    return SignalOutcomeEvaluationRead(
        signal_id=signal_id,
        outcomes=[SignalOutcomeRead.model_validate(outcome) for outcome in outcomes],
    )


@router.get("/signals/{signal_id}/outcomes", response_model=list[SignalOutcomeRead])
async def list_signal_outcomes(
    signal_id: UUID,
    service: Annotated[OutcomeEvaluationService, Depends(get_outcome_service)],
) -> list[SignalOutcomeRead]:
    outcomes = await service.get_signal_outcomes(signal_id)
    return [SignalOutcomeRead.model_validate(outcome) for outcome in outcomes]


@router.get("/signals/{signal_id}/outcomes/{horizon_minutes}", response_model=SignalOutcomeRead)
async def get_signal_outcome(
    signal_id: UUID,
    horizon_minutes: int,
    service: Annotated[OutcomeEvaluationService, Depends(get_outcome_service)],
) -> SignalOutcomeRead:
    outcome = await service.get_signal_outcome(signal_id, horizon_minutes)
    return SignalOutcomeRead.model_validate(outcome)


@router.post(
    "/analysis-runs/{analysis_run_id}/outcomes/evaluate",
    response_model=AnalysisRunOutcomeEvaluationRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def evaluate_analysis_run_outcomes(
    analysis_run_id: UUID,
    payload: OutcomeEvaluationRequest,
    service: Annotated[OutcomeEvaluationService, Depends(get_outcome_service)],
) -> AnalysisRunOutcomeEvaluationRead:
    outcomes = await service.evaluate_analysis_run_outcomes(
        analysis_run_id=analysis_run_id,
        horizons_minutes=payload.horizons_minutes,
        force_recompute=payload.force_recompute,
    )
    return AnalysisRunOutcomeEvaluationRead(
        analysis_run_id=analysis_run_id,
        outcomes=[SignalOutcomeRead.model_validate(outcome) for outcome in outcomes],
    )


@router.get("/analysis-runs/{analysis_run_id}/outcomes", response_model=list[SignalOutcomeRead])
async def list_analysis_run_outcomes(
    analysis_run_id: UUID,
    service: Annotated[OutcomeEvaluationService, Depends(get_outcome_service)],
) -> list[SignalOutcomeRead]:
    outcomes = await service.get_analysis_run_outcomes(analysis_run_id)
    return [SignalOutcomeRead.model_validate(outcome) for outcome in outcomes]


@router.post(
    "/outcome-evaluation-runs/backfill",
    response_model=OutcomeEvaluationRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def backfill_outcomes(
    payload: OutcomeBackfillRequest,
    service: Annotated[OutcomeEvaluationService, Depends(get_outcome_service)],
) -> OutcomeEvaluationRunRead:
    run = await service.backfill_outcomes(payload)
    return OutcomeEvaluationRunRead.model_validate(run)


@router.get("/outcome-evaluation-runs/{run_id}", response_model=OutcomeEvaluationRunRead)
async def get_outcome_evaluation_run(
    run_id: UUID,
    service: Annotated[OutcomeEvaluationService, Depends(get_outcome_service)],
) -> OutcomeEvaluationRunRead:
    run = await service.get_evaluation_run(run_id)
    return OutcomeEvaluationRunRead.model_validate(run)


@router.get("/outcomes/performance/patterns", response_model=list[OutcomePerformanceRead])
async def get_pattern_outcome_performance(
    service: Annotated[OutcomeEvaluationService, Depends(get_outcome_service)],
    workspace_id: UUID,
    horizon_minutes: Annotated[int, Query(gt=0)],
    symbol_id: UUID | None = None,
    timeframe: str | None = None,
    pattern_type: str | None = None,
    strategy_profile_key: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[OutcomePerformanceRead]:
    return await service.aggregate_by_patterns(
        OutcomePerformanceQuery(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            horizon_minutes=horizon_minutes,
            pattern_type=pattern_type,
            strategy_profile_key=strategy_profile_key,
            start_time=start_time,
            end_time=end_time,
        )
    )


@router.get("/outcomes/performance/strategy-profiles", response_model=list[OutcomePerformanceRead])
async def get_strategy_profile_outcome_performance(
    service: Annotated[OutcomeEvaluationService, Depends(get_outcome_service)],
    workspace_id: UUID,
    horizon_minutes: Annotated[int, Query(gt=0)],
    symbol_id: UUID | None = None,
    timeframe: str | None = None,
    pattern_type: str | None = None,
    strategy_profile_key: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[OutcomePerformanceRead]:
    return await service.aggregate_by_strategy_profiles(
        OutcomePerformanceQuery(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            horizon_minutes=horizon_minutes,
            pattern_type=pattern_type,
            strategy_profile_key=strategy_profile_key,
            start_time=start_time,
            end_time=end_time,
        )
    )


@router.get("/outcomes/performance/symbols", response_model=list[OutcomePerformanceRead])
async def get_symbol_outcome_performance(
    service: Annotated[OutcomeEvaluationService, Depends(get_outcome_service)],
    workspace_id: UUID,
    horizon_minutes: Annotated[int, Query(gt=0)],
    symbol_id: UUID | None = None,
    timeframe: str | None = None,
    pattern_type: str | None = None,
    strategy_profile_key: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[OutcomePerformanceRead]:
    return await service.aggregate_by_symbols(
        OutcomePerformanceQuery(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            horizon_minutes=horizon_minutes,
            pattern_type=pattern_type,
            strategy_profile_key=strategy_profile_key,
            start_time=start_time,
            end_time=end_time,
        )
    )
