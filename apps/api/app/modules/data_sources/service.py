from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.data_sources.models import DataSource
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.data_sources.schemas import DataSourceCreate, DataSourceUpdate
from app.modules.provider_credentials.redaction import find_sensitive_payload_paths
from app.modules.provider_credentials.repository import ProviderCredentialRepository


class DataSourceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = DataSourceRepository(session)
        self.provider_credential_repository = ProviderCredentialRepository(session)

    async def create_data_source(self, payload: DataSourceCreate) -> DataSource:
        self.validate_config(payload.config_json)
        if payload.credential_ref_id is not None:
            await self.validate_credential_ref(payload.workspace_id, payload.credential_ref_id)
        data_source = DataSource(**payload.model_dump(mode="python"))
        try:
            created_data_source = await self.repository.create(data_source)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "data_source_conflict",
                "Data source could not be created",
            ) from error
        return created_data_source

    async def list_data_sources(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        source_type: str | None = None,
        status: str | None = None,
    ) -> list[DataSource]:
        return await self.repository.list(
            limit=limit,
            offset=offset,
            workspace_id=workspace_id,
            source_type=source_type,
            status=status,
        )

    async def get_data_source(self, data_source_id: UUID) -> DataSource:
        data_source = await self.repository.get_by_id(data_source_id)
        if data_source is None:
            raise AppError(404, "data_source_not_found", "Data source not found")
        return data_source

    async def update_data_source(
        self,
        data_source_id: UUID,
        payload: DataSourceUpdate,
    ) -> DataSource:
        data_source = await self.get_data_source(data_source_id)
        updates = payload.model_dump(exclude_unset=True, mode="python")
        if payload.config_json is not None:
            self.validate_config(payload.config_json)
        if payload.credential_ref_id is not None:
            await self.validate_credential_ref(data_source.workspace_id, payload.credential_ref_id)
        for field_name, field_value in updates.items():
            setattr(data_source, field_name, field_value)
        try:
            await self.session.flush()
            await self.session.refresh(data_source)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "data_source_conflict",
                "Data source could not be updated",
            ) from error
        return data_source

    async def validate_credential_ref(self, workspace_id: UUID, credential_ref_id: UUID) -> None:
        credential_ref = await self.provider_credential_repository.get_credential_ref(
            credential_ref_id
        )
        if credential_ref is None:
            raise AppError(
                404,
                "provider_credential_ref_not_found",
                "Provider credential reference not found",
            )
        if credential_ref.workspace_id != workspace_id:
            raise AppError(
                422,
                "provider_credential_workspace_mismatch",
                "Provider credential reference does not belong to this workspace",
            )

    def validate_config(self, config_json: dict[str, object]) -> None:
        sensitive_paths = find_sensitive_payload_paths(config_json)
        if sensitive_paths:
            raise AppError(
                422,
                "data_source_config_contains_secret",
                "Data source config must not include inline secrets; use credential_ref_id",
            )
