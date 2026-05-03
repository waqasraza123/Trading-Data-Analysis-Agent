from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.rule_packs.models import RulePackStatus
from app.modules.rule_packs.schemas import (
    ReproducibilityManifestGenerateRequest,
    ReproducibilityManifestRead,
    RulePackCreate,
    RulePackRead,
    RulePackSeedRequest,
)
from app.modules.rule_packs.service import (
    ReproducibilityManifestService,
    RulePackService,
)

router = APIRouter(tags=["rule-packs"])


def get_rule_pack_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> RulePackService:
    return RulePackService(session)


def get_manifest_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ReproducibilityManifestService:
    return ReproducibilityManifestService(session)


@router.post("/rule-packs", response_model=RulePackRead, status_code=status.HTTP_201_CREATED)
async def create_rule_pack(
    payload: RulePackCreate,
    service: Annotated[RulePackService, Depends(get_rule_pack_service)],
) -> RulePackRead:
    rule_pack = await service.create_rule_pack(payload)
    await service.session.commit()
    return RulePackRead.model_validate(rule_pack)


@router.get("/rule-packs", response_model=list[RulePackRead])
async def list_rule_packs(
    service: Annotated[RulePackService, Depends(get_rule_pack_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    workspace_id: UUID | None = None,
    status_filter: Annotated[RulePackStatus | None, Query(alias="status")] = None,
    key: str | None = None,
) -> list[RulePackRead]:
    rule_packs = await service.list_rule_packs(
        limit=limit,
        offset=offset,
        workspace_id=workspace_id,
        status=status_filter,
        key=key,
    )
    return [RulePackRead.model_validate(rule_pack) for rule_pack in rule_packs]


@router.get("/rule-packs/{key}/{version}", response_model=RulePackRead)
async def get_rule_pack(
    key: str,
    version: str,
    service: Annotated[RulePackService, Depends(get_rule_pack_service)],
    workspace_id: UUID | None = None,
) -> RulePackRead:
    rule_pack = await service.get_rule_pack(key, version, workspace_id)
    return RulePackRead.model_validate(rule_pack)


@router.post("/rule-packs/seed-default", response_model=RulePackRead)
async def seed_default_rule_pack(
    service: Annotated[RulePackService, Depends(get_rule_pack_service)],
    payload: Annotated[RulePackSeedRequest | None, Body()] = None,
) -> RulePackRead:
    rule_pack = await service.seed_default_rule_pack(
        workspace_id=payload.workspace_id if payload is not None else None
    )
    await service.session.commit()
    return RulePackRead.model_validate(rule_pack)


@router.post(
    "/analysis-runs/{analysis_run_id}/reproducibility-manifest",
    response_model=ReproducibilityManifestRead,
)
async def generate_analysis_reproducibility_manifest(
    analysis_run_id: UUID,
    service: Annotated[ReproducibilityManifestService, Depends(get_manifest_service)],
    payload: Annotated[ReproducibilityManifestGenerateRequest | None, Body()] = None,
) -> ReproducibilityManifestRead:
    manifest = await service.generate_for_analysis_run(
        analysis_run_id,
        force_recompute=payload.force_recompute if payload is not None else False,
    )
    await service.session.commit()
    return ReproducibilityManifestRead.model_validate(manifest)


@router.get(
    "/analysis-runs/{analysis_run_id}/reproducibility-manifest",
    response_model=ReproducibilityManifestRead,
)
async def get_analysis_reproducibility_manifest(
    analysis_run_id: UUID,
    service: Annotated[ReproducibilityManifestService, Depends(get_manifest_service)],
) -> ReproducibilityManifestRead:
    manifest = await service.get_for_analysis_run(analysis_run_id)
    return ReproducibilityManifestRead.model_validate(manifest)


@router.post(
    "/signals/{signal_id}/reproducibility-manifest",
    response_model=ReproducibilityManifestRead,
)
async def generate_signal_reproducibility_manifest(
    signal_id: UUID,
    service: Annotated[ReproducibilityManifestService, Depends(get_manifest_service)],
    payload: Annotated[ReproducibilityManifestGenerateRequest | None, Body()] = None,
) -> ReproducibilityManifestRead:
    manifest = await service.generate_for_signal(
        signal_id,
        force_recompute=payload.force_recompute if payload is not None else False,
    )
    await service.session.commit()
    return ReproducibilityManifestRead.model_validate(manifest)


@router.get(
    "/signals/{signal_id}/reproducibility-manifest",
    response_model=ReproducibilityManifestRead,
)
async def get_signal_reproducibility_manifest(
    signal_id: UUID,
    service: Annotated[ReproducibilityManifestService, Depends(get_manifest_service)],
) -> ReproducibilityManifestRead:
    manifest = await service.get_for_signal(signal_id)
    return ReproducibilityManifestRead.model_validate(manifest)
