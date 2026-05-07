from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.equity_research.models import (
    EquitySwingCandidateStatus,
    EquitySwingScanRunStatus,
    EquityUniverseStatus,
)
from app.modules.equity_research.schemas import (
    EquityCatalystContextCreate,
    EquityCatalystContextRead,
    EquitySwingCandidateRead,
    EquitySwingScanCreate,
    EquitySwingScanRunRead,
    EquityUniverseCreate,
    EquityUniverseMemberCreate,
    EquityUniverseMemberRead,
    EquityUniverseMembersBulkCreate,
    EquityUniverseRead,
    EquityUniverseUpdate,
)
from app.modules.equity_research.service import EquityResearchService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/equity-research", tags=["equity-research"])


def get_equity_research_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> EquityResearchService:
    return EquityResearchService(session)


@router.post(
    "/universes",
    response_model=EquityUniverseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.SCANS_WRITE))],
)
async def create_universe(
    payload: EquityUniverseCreate,
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
) -> EquityUniverseRead:
    universe = await service.create_universe(payload)
    return EquityUniverseRead.model_validate(universe)


@router.get("/universes", response_model=list[EquityUniverseRead])
async def list_universes(
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
    workspace_id: UUID,
    status_filter: Annotated[EquityUniverseStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EquityUniverseRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    universes = await service.list_universes(
        workspace_id=workspace_id,
        status=status_filter,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [EquityUniverseRead.model_validate(universe) for universe in universes]


@router.get("/universes/{universe_id}", response_model=EquityUniverseRead)
async def get_universe(
    universe_id: UUID,
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
) -> EquityUniverseRead:
    universe = await service.get_universe(universe_id)
    return EquityUniverseRead.model_validate(universe)


@router.patch(
    "/universes/{universe_id}",
    response_model=EquityUniverseRead,
    dependencies=[Depends(require_permission(Permission.SCANS_WRITE))],
)
async def update_universe(
    universe_id: UUID,
    payload: EquityUniverseUpdate,
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
) -> EquityUniverseRead:
    universe = await service.update_universe(universe_id, payload)
    return EquityUniverseRead.model_validate(universe)


@router.post(
    "/universes/{universe_id}/members",
    response_model=EquityUniverseMemberRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.SCANS_WRITE))],
)
async def add_universe_member(
    universe_id: UUID,
    payload: EquityUniverseMemberCreate,
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
) -> EquityUniverseMemberRead:
    member = await service.add_universe_member(universe_id, payload)
    return EquityUniverseMemberRead.model_validate(member)


@router.post(
    "/universes/{universe_id}/members/bulk",
    response_model=list[EquityUniverseMemberRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.SCANS_WRITE))],
)
async def add_universe_members_bulk(
    universe_id: UUID,
    payload: EquityUniverseMembersBulkCreate,
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
) -> list[EquityUniverseMemberRead]:
    members = await service.add_universe_members_bulk(universe_id, payload)
    return [EquityUniverseMemberRead.model_validate(member) for member in members]


@router.get("/universes/{universe_id}/members", response_model=list[EquityUniverseMemberRead])
async def list_universe_members(
    universe_id: UUID,
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
    is_active: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EquityUniverseMemberRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    members = await service.list_universe_members(
        universe_id=universe_id,
        is_active=is_active,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [EquityUniverseMemberRead.model_validate(member) for member in members]


@router.delete(
    "/universes/{universe_id}/members/{member_id}",
    response_model=EquityUniverseMemberRead,
    dependencies=[Depends(require_permission(Permission.SCANS_WRITE))],
)
async def remove_universe_member(
    universe_id: UUID,
    member_id: UUID,
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
) -> EquityUniverseMemberRead:
    member = await service.remove_universe_member(universe_id, member_id)
    return EquityUniverseMemberRead.model_validate(member)


@router.post(
    "/swing-scans",
    response_model=EquitySwingScanRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.SCANS_WRITE))],
)
async def run_swing_scan(
    payload: EquitySwingScanCreate,
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
) -> EquitySwingScanRunRead:
    run = await service.run_swing_scan(payload)
    return EquitySwingScanRunRead.model_validate(run)


@router.get("/swing-scans", response_model=list[EquitySwingScanRunRead])
async def list_swing_scans(
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
    workspace_id: UUID,
    status_filter: Annotated[EquitySwingScanRunStatus | None, Query(alias="status")] = None,
    universe_id: UUID | None = None,
    watchlist_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EquitySwingScanRunRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    runs = await service.list_scan_runs(
        workspace_id=workspace_id,
        status=status_filter,
        universe_id=universe_id,
        watchlist_id=watchlist_id,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [EquitySwingScanRunRead.model_validate(run) for run in runs]


@router.get("/swing-scans/{scan_run_id}", response_model=EquitySwingScanRunRead)
async def get_swing_scan(
    scan_run_id: UUID,
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
) -> EquitySwingScanRunRead:
    run = await service.get_scan_run(scan_run_id)
    return EquitySwingScanRunRead.model_validate(run)


@router.get(
    "/swing-scans/{scan_run_id}/candidates",
    response_model=list[EquitySwingCandidateRead],
)
async def list_swing_scan_candidates(
    scan_run_id: UUID,
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
    candidate_status: EquitySwingCandidateStatus | None = None,
    setup_type: str | None = None,
    setup_quality_label: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EquitySwingCandidateRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    candidates = await service.list_candidates(
        scan_run_id=scan_run_id,
        limit=pagination.limit,
        offset=pagination.offset,
        candidate_status=candidate_status,
        setup_type=setup_type,
        setup_quality_label=setup_quality_label,
    )
    return [EquitySwingCandidateRead.model_validate(candidate) for candidate in candidates]


@router.get("/candidates/{candidate_id}", response_model=EquitySwingCandidateRead)
async def get_candidate(
    candidate_id: UUID,
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
) -> EquitySwingCandidateRead:
    candidate = await service.get_candidate(candidate_id)
    return EquitySwingCandidateRead.model_validate(candidate)


@router.post(
    "/catalysts",
    response_model=EquityCatalystContextRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.MARKET_DATA_WRITE))],
)
async def create_catalyst(
    payload: EquityCatalystContextCreate,
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
) -> EquityCatalystContextRead:
    catalyst = await service.create_catalyst(payload)
    return EquityCatalystContextRead.model_validate(catalyst)


@router.get("/catalysts", response_model=list[EquityCatalystContextRead])
async def list_catalysts(
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
    workspace_id: UUID,
    symbol_id: UUID | None = None,
    catalyst_type: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EquityCatalystContextRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    catalysts = await service.list_catalysts(
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        catalyst_type=catalyst_type,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [EquityCatalystContextRead.model_validate(catalyst) for catalyst in catalysts]


@router.get("/symbols/{symbol_id}/catalysts", response_model=list[EquityCatalystContextRead])
async def list_symbol_catalysts(
    symbol_id: UUID,
    service: Annotated[EquityResearchService, Depends(get_equity_research_service)],
    workspace_id: UUID,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EquityCatalystContextRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    catalysts = await service.list_catalysts(
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        catalyst_type=None,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [EquityCatalystContextRead.model_validate(catalyst) for catalyst in catalysts]
