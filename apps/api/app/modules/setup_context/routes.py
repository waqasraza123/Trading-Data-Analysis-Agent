from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.setup_context.schemas import SetupContextRead
from app.modules.setup_context.service import SetupContextService

router = APIRouter(tags=["setup-context"])


def get_setup_context_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> SetupContextService:
    return SetupContextService(session)


@router.post(
    "/signals/{signal_id}/setup-context",
    response_model=SetupContextRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def build_signal_setup_context(
    signal_id: UUID,
    service: Annotated[SetupContextService, Depends(get_setup_context_service)],
    force_recompute: Annotated[bool, Query(alias="forceRecompute")] = False,
) -> SetupContextRead:
    setup_context = await service.build_for_signal(
        signal_id=signal_id,
        force_recompute=force_recompute,
    )
    return SetupContextRead.model_validate(setup_context)


@router.get("/signals/{signal_id}/setup-context", response_model=SetupContextRead)
async def get_signal_setup_context(
    signal_id: UUID,
    service: Annotated[SetupContextService, Depends(get_setup_context_service)],
) -> SetupContextRead:
    setup_context = await service.get_for_signal(signal_id)
    return SetupContextRead.model_validate(setup_context)


@router.post(
    "/analysis-runs/{analysis_run_id}/setup-context",
    response_model=SetupContextRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def build_analysis_run_setup_context(
    analysis_run_id: UUID,
    service: Annotated[SetupContextService, Depends(get_setup_context_service)],
    force_recompute: Annotated[bool, Query(alias="forceRecompute")] = False,
) -> SetupContextRead:
    setup_context = await service.build_for_analysis_run(
        analysis_run_id=analysis_run_id,
        force_recompute=force_recompute,
    )
    return SetupContextRead.model_validate(setup_context)


@router.get("/analysis-runs/{analysis_run_id}/setup-context", response_model=SetupContextRead)
async def get_analysis_run_setup_context(
    analysis_run_id: UUID,
    service: Annotated[SetupContextService, Depends(get_setup_context_service)],
) -> SetupContextRead:
    setup_context = await service.get_for_analysis_run(analysis_run_id)
    return SetupContextRead.model_validate(setup_context)
