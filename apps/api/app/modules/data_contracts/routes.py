from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.data_contracts.models import DataContractStatus, DataContractValidationStatus
from app.modules.data_contracts.schemas import (
    DataContractRead,
    DataContractSeedRead,
    DataContractSourceValidationRequest,
    DataContractValidationQuery,
    DataContractValidationRead,
    DataContractValidationRequest,
    DataContractValidationResult,
)
from app.modules.data_contracts.service import DataContractService

router = APIRouter(prefix="/data-contracts", tags=["data-contracts"])


def get_data_contract_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> DataContractService:
    return DataContractService(session)


@router.get("", response_model=list[DataContractRead])
async def list_contracts(
    service: Annotated[DataContractService, Depends(get_data_contract_service)],
    status_filter: Annotated[DataContractStatus | None, Query(alias="status")] = None,
) -> list[DataContractRead]:
    contracts = await service.list_contracts(status_filter)
    return [DataContractRead.model_validate(contract) for contract in contracts]


@router.get("/{key}/{version}", response_model=DataContractRead)
async def get_contract(
    key: str,
    version: str,
    service: Annotated[DataContractService, Depends(get_data_contract_service)],
) -> DataContractRead:
    contract = await service.get_contract(key, version)
    return DataContractRead.model_validate(contract)


@router.post(
    "/seed-default",
    response_model=DataContractSeedRead,
    status_code=status.HTTP_200_OK,
)
async def seed_default_contracts(
    service: Annotated[DataContractService, Depends(get_data_contract_service)],
) -> DataContractSeedRead:
    contracts = await service.seed_default_contracts()
    await service.session.commit()
    return DataContractSeedRead(
        seeded_count=len(contracts),
        contract_keys=[f"{contract.key}.{contract.version}" for contract in contracts],
    )


@router.post("/validate", response_model=DataContractValidationResult)
async def validate_payload(
    request: DataContractValidationRequest,
    service: Annotated[DataContractService, Depends(get_data_contract_service)],
) -> DataContractValidationResult:
    outcome, validation = await service.validate_payload(
        key=request.key,
        version=request.version,
        payload=request.payload,
        workspace_id=request.workspace_id,
        source_type=request.source_type,
        source_id=request.source_id,
        strict=request.strict,
    )
    await service.session.commit()
    return DataContractValidationResult(
        contract_key=request.key,
        contract_version=request.version,
        status=outcome.status,
        errors=outcome.errors,
        warnings=outcome.warnings,
        payload_summary=outcome.payload_summary,
        validation=DataContractValidationRead.model_validate(validation),
    )


@router.post("/validate-source", response_model=DataContractValidationResult)
async def validate_source_payload(
    request: DataContractSourceValidationRequest,
    service: Annotated[DataContractService, Depends(get_data_contract_service)],
) -> DataContractValidationResult:
    outcome, validation = await service.validate_source_payload(
        source_type=request.source_type,
        source_id=request.source_id,
        contract_key=request.contract_key,
        version=request.version,
        strict=request.strict,
    )
    await service.session.commit()
    return DataContractValidationResult(
        contract_key=request.contract_key,
        contract_version=request.version,
        status=outcome.status,
        errors=outcome.errors,
        warnings=outcome.warnings,
        payload_summary=outcome.payload_summary,
        validation=DataContractValidationRead.model_validate(validation),
    )


@router.get("/validations", response_model=list[DataContractValidationRead])
async def list_validations(
    service: Annotated[DataContractService, Depends(get_data_contract_service)],
    workspace_id: UUID | None = None,
    contract_key: str | None = None,
    contract_version: str | None = None,
    source_type: str | None = None,
    source_id: UUID | None = None,
    validation_status: Annotated[
        DataContractValidationStatus | None,
        Query(alias="status"),
    ] = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[DataContractValidationRead]:
    query = DataContractValidationQuery(
        workspace_id=workspace_id,
        contract_key=contract_key,
        contract_version=contract_version,
        source_type=source_type,
        source_id=source_id,
        status=validation_status,
        limit=limit,
    )
    validations = await service.list_validations(query)
    return [DataContractValidationRead.model_validate(validation) for validation in validations]
