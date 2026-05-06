from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.read_models.schemas import (
    CommandCenterReadModelRead,
    DashboardSymbolReadModelFilters,
    DashboardSymbolReadModelRead,
    RebuildCommandCenterRequest,
    RebuildSymbolReadModelRequest,
    RebuildWorkspaceSignalCardsRequest,
    RebuildWorkspaceSignalCardsResponse,
    SignalCardReadModelFilters,
    SignalCardReadModelRead,
)
from app.modules.read_models.service import ReadModelService

router = APIRouter(prefix="/read-models", tags=["read-models"])


def get_read_model_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ReadModelService:
    return ReadModelService(session)


@router.post(
    "/symbols/rebuild",
    response_model=DashboardSymbolReadModelRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def rebuild_symbol_read_model(
    request: RebuildSymbolReadModelRequest,
    service: Annotated[ReadModelService, Depends(get_read_model_service)],
) -> DashboardSymbolReadModelRead:
    model = await service.rebuild_symbol_read_model(
        workspace_id=request.workspace_id,
        symbol_id=request.symbol_id,
        timeframe=request.timeframe,
        source_id=request.source_id,
    )
    return DashboardSymbolReadModelRead.model_validate(model)


@router.get("/symbols", response_model=list[DashboardSymbolReadModelRead])
async def get_dashboard_symbols(
    service: Annotated[ReadModelService, Depends(get_read_model_service)],
    workspace_id: Annotated[UUID, Query(alias="workspaceId")],
    symbol_id: Annotated[UUID | None, Query(alias="symbolId")] = None,
    source_id: Annotated[UUID | None, Query(alias="sourceId")] = None,
    timeframe: str | None = None,
    freshness_label: Annotated[str | None, Query(alias="freshnessLabel")] = None,
    data_quality_label: Annotated[str | None, Query(alias="dataQualityLabel")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DashboardSymbolReadModelRead]:
    models = await service.get_dashboard_symbols(
        DashboardSymbolReadModelFilters(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
            timeframe=timeframe,
            freshness_label=freshness_label,
            data_quality_label=data_quality_label,
            limit=limit,
            offset=offset,
        )
    )
    return [DashboardSymbolReadModelRead.model_validate(model) for model in models]


@router.post(
    "/signals/{signal_id}/rebuild",
    response_model=SignalCardReadModelRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def rebuild_signal_card(
    signal_id: UUID,
    service: Annotated[ReadModelService, Depends(get_read_model_service)],
) -> SignalCardReadModelRead:
    card = await service.rebuild_signal_card(signal_id)
    return SignalCardReadModelRead.model_validate(card)


@router.post(
    "/signals/rebuild-workspace",
    response_model=RebuildWorkspaceSignalCardsResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def rebuild_workspace_signal_cards(
    request: RebuildWorkspaceSignalCardsRequest,
    service: Annotated[ReadModelService, Depends(get_read_model_service)],
) -> RebuildWorkspaceSignalCardsResponse:
    cards, skipped_count = await service.rebuild_workspace_signal_cards(
        workspace_id=request.workspace_id,
        limit=request.limit,
    )
    return RebuildWorkspaceSignalCardsResponse(
        workspace_id=request.workspace_id,
        requested_limit=request.limit,
        rebuilt_count=len(cards),
        skipped_count=skipped_count,
        cards=[SignalCardReadModelRead.model_validate(card) for card in cards],
    )


@router.get("/signals", response_model=list[SignalCardReadModelRead])
async def get_signal_cards(
    service: Annotated[ReadModelService, Depends(get_read_model_service)],
    workspace_id: Annotated[UUID, Query(alias="workspaceId")],
    symbol_id: Annotated[UUID | None, Query(alias="symbolId")] = None,
    timeframe: str | None = None,
    classification_status: Annotated[str | None, Query(alias="classificationStatus")] = None,
    bias: str | None = None,
    review_bucket: Annotated[str | None, Query(alias="reviewBucket")] = None,
    priority_label: Annotated[str | None, Query(alias="priorityLabel")] = None,
    freshness_label: Annotated[str | None, Query(alias="freshnessLabel")] = None,
    data_quality_label: Annotated[str | None, Query(alias="dataQualityLabel")] = None,
    readiness_label: Annotated[str | None, Query(alias="readinessLabel")] = None,
    search: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SignalCardReadModelRead]:
    cards = await service.get_signal_cards(
        SignalCardReadModelFilters(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            timeframe=timeframe,
            classification_status=classification_status,
            bias=bias,
            review_bucket=review_bucket,
            priority_label=priority_label,
            freshness_label=freshness_label,
            data_quality_label=data_quality_label,
            readiness_label=readiness_label,
            search=search,
            limit=limit,
            offset=offset,
        )
    )
    return [SignalCardReadModelRead.model_validate(card) for card in cards]


@router.post(
    "/command-center/rebuild",
    response_model=CommandCenterReadModelRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def rebuild_command_center(
    request: RebuildCommandCenterRequest,
    service: Annotated[ReadModelService, Depends(get_read_model_service)],
) -> CommandCenterReadModelRead:
    model = await service.rebuild_command_center(
        workspace_id=request.workspace_id,
        period_start=request.period_start,
        period_end=request.period_end,
    )
    return CommandCenterReadModelRead.model_validate(model)


@router.get("/command-center", response_model=CommandCenterReadModelRead)
async def get_command_center(
    service: Annotated[ReadModelService, Depends(get_read_model_service)],
    workspace_id: Annotated[UUID, Query(alias="workspaceId")],
) -> CommandCenterReadModelRead:
    model = await service.get_command_center(workspace_id)
    return CommandCenterReadModelRead.model_validate(model)
