from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.advanced_features.schemas import AdvancedFeatureSnapshotRead
from app.modules.advanced_features.service import AdvancedFeatureSnapshotService

router = APIRouter(tags=["advanced-features"])


def get_advanced_feature_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> AdvancedFeatureSnapshotService:
    return AdvancedFeatureSnapshotService(session)


@router.post(
    "/analysis-runs/{analysis_run_id}/advanced-features",
    response_model=AdvancedFeatureSnapshotRead,
)
async def generate_analysis_run_advanced_features(
    analysis_run_id: UUID,
    service: Annotated[AdvancedFeatureSnapshotService, Depends(get_advanced_feature_service)],
    force_recompute: Annotated[bool, Query(alias="forceRecompute")] = False,
) -> AdvancedFeatureSnapshotRead:
    snapshot = await service.generate_for_analysis_run(
        analysis_run_id,
        force_recompute=force_recompute,
    )
    return AdvancedFeatureSnapshotRead.model_validate(snapshot)


@router.get(
    "/analysis-runs/{analysis_run_id}/advanced-features",
    response_model=AdvancedFeatureSnapshotRead,
)
async def get_analysis_run_advanced_features(
    analysis_run_id: UUID,
    service: Annotated[AdvancedFeatureSnapshotService, Depends(get_advanced_feature_service)],
) -> AdvancedFeatureSnapshotRead:
    snapshot = await service.get_for_analysis_run(analysis_run_id)
    return AdvancedFeatureSnapshotRead.model_validate(snapshot)


@router.post("/signals/{signal_id}/advanced-features", response_model=AdvancedFeatureSnapshotRead)
async def generate_signal_advanced_features(
    signal_id: UUID,
    service: Annotated[AdvancedFeatureSnapshotService, Depends(get_advanced_feature_service)],
    force_recompute: Annotated[bool, Query(alias="forceRecompute")] = False,
) -> AdvancedFeatureSnapshotRead:
    snapshot = await service.generate_for_signal(signal_id, force_recompute=force_recompute)
    return AdvancedFeatureSnapshotRead.model_validate(snapshot)


@router.get("/signals/{signal_id}/advanced-features", response_model=AdvancedFeatureSnapshotRead)
async def get_signal_advanced_features(
    signal_id: UUID,
    service: Annotated[AdvancedFeatureSnapshotService, Depends(get_advanced_feature_service)],
) -> AdvancedFeatureSnapshotRead:
    snapshot = await service.get_for_signal(signal_id)
    return AdvancedFeatureSnapshotRead.model_validate(snapshot)
