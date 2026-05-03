from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.data_contracts.models import (
    DataContract,
    DataContractStatus,
    DataContractValidation,
)
from app.modules.data_contracts.registry import DEFAULT_DATA_CONTRACTS
from app.modules.data_contracts.repository import DataContractRepository
from app.modules.data_contracts.schemas import DataContractValidationQuery
from app.modules.data_contracts.validators import (
    DataContractValidationOutcome,
    validate_payload_against_schema,
)


class DataContractService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = DataContractRepository(session)

    async def seed_default_contracts(self) -> list[DataContract]:
        seeded_contracts: list[DataContract] = []
        for definition in DEFAULT_DATA_CONTRACTS:
            existing_contract = await self.repository.get_contract(
                definition.key,
                definition.version,
            )
            if existing_contract is None:
                existing_contract = await self.repository.create_contract(
                    DataContract(
                        key=definition.key,
                        version=definition.version,
                        status=DataContractStatus.ACTIVE.value,
                        description=definition.description,
                        schema_json=definition.schema_json,
                        metadata_json=definition.metadata_json,
                    )
                )
            else:
                existing_contract.status = DataContractStatus.ACTIVE.value
                existing_contract.description = definition.description
                existing_contract.schema_json = definition.schema_json
                existing_contract.metadata_json = definition.metadata_json
            seeded_contracts.append(existing_contract)
        await self.session.flush()
        return seeded_contracts

    async def list_contracts(self, status: DataContractStatus | None = None) -> list[DataContract]:
        return await self.repository.list_contracts(status.value if status is not None else None)

    async def get_contract(self, key: str, version: str) -> DataContract:
        contract = await self.repository.get_contract(key, version)
        if contract is None:
            raise AppError(404, "data_contract_not_found", "Data contract not found")
        return contract

    async def validate_payload(
        self,
        key: str,
        version: str,
        payload: dict[str, Any] | list[Any],
        workspace_id: UUID | None = None,
        source_type: str | None = None,
        source_id: UUID | None = None,
        strict: bool = False,
    ) -> tuple[DataContractValidationOutcome, DataContractValidation]:
        contract = await self.get_contract(key, version)
        outcome = validate_payload_against_schema(payload, contract.schema_json, strict)
        validation = await self.repository.create_validation(
            DataContractValidation(
                workspace_id=workspace_id,
                contract_key=contract.key,
                contract_version=contract.version,
                source_type=source_type,
                source_id=source_id,
                status=outcome.status.value,
                validation_errors_json=outcome.errors,
                validation_warnings_json=outcome.warnings,
                payload_summary_json=outcome.payload_summary,
            )
        )
        return outcome, validation

    async def validate_source_payload(
        self,
        source_type: str,
        source_id: UUID,
        contract_key: str,
        version: str,
        strict: bool = False,
    ) -> tuple[DataContractValidationOutcome, DataContractValidation]:
        source_payload = await self.repository.get_source_payload(source_type, source_id)
        if source_payload is None:
            raise AppError(
                404,
                "source_payload_not_found",
                "Source payload was not found or is not supported for validation",
            )
        workspace_id, payload = source_payload
        return await self.validate_payload(
            key=contract_key,
            version=version,
            payload=payload,
            workspace_id=workspace_id,
            source_type=source_type,
            source_id=source_id,
            strict=strict,
        )

    async def list_validations(
        self,
        query: DataContractValidationQuery,
    ) -> list[DataContractValidation]:
        return await self.repository.list_validations(
            workspace_id=query.workspace_id,
            contract_key=query.contract_key,
            contract_version=query.contract_version,
            source_type=query.source_type,
            source_id=query.source_id,
            status=query.status.value if query.status is not None else None,
            limit=query.limit,
        )
