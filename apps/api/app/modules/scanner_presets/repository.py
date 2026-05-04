from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_sources.models import DataSource
from app.modules.preference_profiles.models import PersonalStrategyPreferenceProfile
from app.modules.scanner_presets.models import ScannerPreset, ScannerPresetApplication
from app.modules.symbols.models import Symbol
from app.modules.workspaces.models import Workspace


class ScannerPresetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_preset(self, preset: ScannerPreset) -> ScannerPreset:
        self.session.add(preset)
        await self.session.flush()
        await self.session.refresh(preset)
        return preset

    async def get_preset_by_id(self, preset_id: UUID) -> ScannerPreset | None:
        return await self.session.get(ScannerPreset, preset_id)

    async def get_by_key_version(
        self,
        key: str,
        preset_version: str,
        workspace_id: UUID | None = None,
    ) -> ScannerPreset | None:
        statement: Select[tuple[ScannerPreset]] = select(ScannerPreset).where(
            ScannerPreset.key == key,
            ScannerPreset.preset_version == preset_version,
        )
        if workspace_id is None:
            statement = statement.where(ScannerPreset.workspace_id.is_(None))
        else:
            statement = statement.where(ScannerPreset.workspace_id == workspace_id)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_active_by_key(
        self,
        key: str,
        preset_version: str | None = None,
        workspace_id: UUID | None = None,
    ) -> ScannerPreset | None:
        statement: Select[tuple[ScannerPreset]] = select(ScannerPreset).where(
            ScannerPreset.key == key,
            ScannerPreset.status == "active",
        )
        if preset_version is not None:
            statement = statement.where(ScannerPreset.preset_version == preset_version)
        if workspace_id is None:
            statement = statement.where(ScannerPreset.workspace_id.is_(None))
        else:
            statement = statement.where(
                or_(
                    ScannerPreset.workspace_id == workspace_id,
                    ScannerPreset.workspace_id.is_(None),
                )
            )
        statement = statement.order_by(
            ScannerPreset.workspace_id.is_not(None).desc(),
            ScannerPreset.updated_at.desc(),
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_presets(
        self,
        workspace_id: UUID | None,
        category: str | None,
        status: str | None,
    ) -> list[ScannerPreset]:
        statement: Select[tuple[ScannerPreset]] = select(ScannerPreset).order_by(
            ScannerPreset.category.asc(),
            ScannerPreset.name.asc(),
        )
        if workspace_id is None:
            statement = statement.where(ScannerPreset.workspace_id.is_(None))
        else:
            statement = statement.where(
                or_(
                    ScannerPreset.workspace_id == workspace_id,
                    ScannerPreset.workspace_id.is_(None),
                )
            )
        if category is not None:
            statement = statement.where(ScannerPreset.category == category)
        if status is not None:
            statement = statement.where(ScannerPreset.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_application(
        self,
        application: ScannerPresetApplication,
    ) -> ScannerPresetApplication:
        self.session.add(application)
        await self.session.flush()
        await self.session.refresh(application)
        return application

    async def get_application(self, application_id: UUID) -> ScannerPresetApplication | None:
        return await self.session.get(ScannerPresetApplication, application_id)

    async def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        return await self.session.get(Workspace, workspace_id)

    async def get_data_source(self, source_id: UUID) -> DataSource | None:
        return await self.session.get(DataSource, source_id)

    async def get_preference_profile(
        self,
        profile_id: UUID,
    ) -> PersonalStrategyPreferenceProfile | None:
        return await self.session.get(PersonalStrategyPreferenceProfile, profile_id)

    async def get_symbols_by_ids(self, symbol_ids: list[UUID]) -> list[Symbol]:
        if not symbol_ids:
            return []
        result = await self.session.execute(
            select(Symbol).where(Symbol.id.in_(symbol_ids), Symbol.is_active.is_(True))
        )
        found = list(result.scalars().all())
        by_id = {item.id: item for item in found}
        return [by_id[symbol_id] for symbol_id in symbol_ids if symbol_id in by_id]

    async def get_symbols_by_codes(self, symbol_codes: list[str]) -> list[Symbol]:
        normalized_codes = [code.strip().upper() for code in symbol_codes if code.strip()]
        if not normalized_codes:
            return []
        result = await self.session.execute(
            select(Symbol)
            .where(Symbol.symbol.in_(normalized_codes), Symbol.is_active.is_(True))
            .order_by(Symbol.symbol.asc())
        )
        found = list(result.scalars().all())
        by_code = {item.symbol: item for item in found}
        return [by_code[code] for code in normalized_codes if code in by_code]
