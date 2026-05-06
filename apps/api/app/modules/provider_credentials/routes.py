from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.provider_credentials.models import (
    ProviderConnectionTestType,
    ProviderCredentialStatus,
    ProviderCredentialType,
)
from app.modules.provider_credentials.schemas import (
    ProviderConfigurationTestRequest,
    ProviderConnectionTestRead,
    ProviderCredentialListFilters,
    ProviderCredentialRefCreate,
    ProviderCredentialRefRead,
    ProviderCredentialRefUpdate,
    ProviderCredentialTestRequest,
)
from app.modules.provider_credentials.service import ProviderCredentialService

router = APIRouter(prefix="/provider-credentials", tags=["provider-credentials"])


def get_provider_credential_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ProviderCredentialService:
    return ProviderCredentialService(session=session, settings=request.app.state.settings)


@router.post(
    "",
    response_model=ProviderCredentialRefRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
)
async def create_credential_ref(
    payload: ProviderCredentialRefCreate,
    service: Annotated[
        ProviderCredentialService,
        Depends(get_provider_credential_service),
    ],
) -> ProviderCredentialRefRead:
    credential_ref = await service.create_credential_ref(payload)
    return service.to_read_schema(credential_ref)


@router.get("", response_model=list[ProviderCredentialRefRead])
async def list_credential_refs(
    service: Annotated[
        ProviderCredentialService,
        Depends(get_provider_credential_service),
    ],
    workspace_id: UUID | None = None,
    provider: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
    status_filter: Annotated[ProviderCredentialStatus | None, Query(alias="status")] = None,
    credential_type: ProviderCredentialType | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ProviderCredentialRefRead]:
    pagination = PaginationParams(limit=limit, offset=offset)
    filters = ProviderCredentialListFilters(
        workspace_id=workspace_id,
        provider=provider,
        status=status_filter,
        credential_type=credential_type,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    credential_refs = await service.list_credential_refs(
        limit=filters.limit,
        offset=filters.offset,
        workspace_id=filters.workspace_id,
        provider=filters.provider,
        status=filters.status,
        credential_type=filters.credential_type,
    )
    return [service.to_read_schema(credential_ref) for credential_ref in credential_refs]


@router.post(
    "/test-provider",
    response_model=ProviderConnectionTestRead,
    dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
)
async def test_provider_configuration(
    payload: ProviderConfigurationTestRequest,
    service: Annotated[
        ProviderCredentialService,
        Depends(get_provider_credential_service),
    ],
) -> ProviderConnectionTestRead:
    connection_test = await service.test_provider_configuration(payload)
    return ProviderConnectionTestRead.model_validate(connection_test)


@router.get("/tests/{test_id}", response_model=ProviderConnectionTestRead)
async def get_connection_test(
    test_id: UUID,
    service: Annotated[
        ProviderCredentialService,
        Depends(get_provider_credential_service),
    ],
) -> ProviderConnectionTestRead:
    connection_test = await service.get_connection_test(test_id)
    return ProviderConnectionTestRead.model_validate(connection_test)


@router.get("/{credential_ref_id}", response_model=ProviderCredentialRefRead)
async def get_credential_ref(
    credential_ref_id: UUID,
    service: Annotated[
        ProviderCredentialService,
        Depends(get_provider_credential_service),
    ],
) -> ProviderCredentialRefRead:
    credential_ref = await service.get_credential_ref(credential_ref_id)
    return service.to_read_schema(credential_ref)


@router.patch(
    "/{credential_ref_id}",
    response_model=ProviderCredentialRefRead,
    dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
)
async def update_credential_ref(
    credential_ref_id: UUID,
    payload: ProviderCredentialRefUpdate,
    service: Annotated[
        ProviderCredentialService,
        Depends(get_provider_credential_service),
    ],
) -> ProviderCredentialRefRead:
    credential_ref = await service.update_credential_ref(credential_ref_id, payload)
    return service.to_read_schema(credential_ref)


@router.post(
    "/{credential_ref_id}/pause",
    response_model=ProviderCredentialRefRead,
    dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
)
async def pause_credential_ref(
    credential_ref_id: UUID,
    service: Annotated[
        ProviderCredentialService,
        Depends(get_provider_credential_service),
    ],
) -> ProviderCredentialRefRead:
    credential_ref = await service.pause_credential_ref(credential_ref_id)
    return service.to_read_schema(credential_ref)


@router.post(
    "/{credential_ref_id}/revoke",
    response_model=ProviderCredentialRefRead,
    dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
)
async def revoke_credential_ref(
    credential_ref_id: UUID,
    service: Annotated[
        ProviderCredentialService,
        Depends(get_provider_credential_service),
    ],
) -> ProviderCredentialRefRead:
    credential_ref = await service.revoke_credential_ref(credential_ref_id)
    return service.to_read_schema(credential_ref)


@router.post(
    "/{credential_ref_id}/test",
    response_model=ProviderConnectionTestRead,
    dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
)
async def test_credential_ref(
    credential_ref_id: UUID,
    service: Annotated[
        ProviderCredentialService,
        Depends(get_provider_credential_service),
    ],
    payload: ProviderCredentialTestRequest | None = None,
) -> ProviderConnectionTestRead:
    test_type: ProviderConnectionTestType | None = payload.test_type if payload else None
    connection_test = await service.test_credential_ref(credential_ref_id, test_type)
    return ProviderConnectionTestRead.model_validate(connection_test)
