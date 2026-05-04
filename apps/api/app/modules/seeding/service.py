from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.data_sources.models import DataSource
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.data_sources.seeds import default_data_sources
from app.modules.engine_versions.service import EngineVersionService
from app.modules.scanner_presets.service import ScannerPresetService
from app.modules.strategy_profiles.service import StrategyProfileService
from app.modules.symbols.models import Symbol
from app.modules.symbols.repository import SymbolRepository
from app.modules.symbols.seeds import DEFAULT_SYMBOLS
from app.modules.users.models import User, UserRole
from app.modules.users.repository import UserRepository
from app.modules.workspaces.models import Workspace
from app.modules.workspaces.repository import WorkspaceRepository


@dataclass(frozen=True)
class SeedResult:
    workspace_id: UUID | None
    admin_user_id: UUID | None
    symbol_count: int
    data_source_count: int
    strategy_profile_count: int
    engine_version_count: int
    scanner_preset_count: int


class SeedService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.workspace_repository = WorkspaceRepository(session)
        self.user_repository = UserRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.data_source_repository = DataSourceRepository(session)
        self.strategy_profile_service = StrategyProfileService(session)
        self.engine_version_service = EngineVersionService(session)
        self.scanner_preset_service = ScannerPresetService(session)

    async def seed(self, settings: Settings) -> SeedResult:
        workspace = await self.seed_workspace(settings.seed_default_workspace_name)
        admin_user = await self.seed_admin_user(settings, workspace)
        symbols = await self.seed_symbols()
        data_sources = await self.seed_data_sources(workspace)
        strategy_profiles = await self.strategy_profile_service.seed_default_profiles()
        engine_versions = await self.engine_version_service.seed_current_versions()
        scanner_presets = await self.scanner_preset_service.seed_default_presets(commit=False)
        await self.session.commit()
        return SeedResult(
            workspace_id=workspace.id if workspace is not None else None,
            admin_user_id=admin_user.id if admin_user is not None else None,
            symbol_count=len(symbols),
            data_source_count=len(data_sources),
            strategy_profile_count=len(strategy_profiles),
            engine_version_count=len(engine_versions),
            scanner_preset_count=len(scanner_presets),
        )

    async def seed_workspace(self, workspace_name: str | None) -> Workspace | None:
        if workspace_name is None or workspace_name.strip() == "":
            return None
        normalized_name = workspace_name.strip()
        workspace = await self.workspace_repository.get_by_name(normalized_name)
        if workspace is not None:
            return workspace
        return await self.workspace_repository.create(Workspace(name=normalized_name))

    async def seed_admin_user(self, settings: Settings, workspace: Workspace | None) -> User | None:
        if workspace is None or settings.seed_default_admin_email is None:
            return None
        email = settings.seed_default_admin_email.strip().lower()
        if email == "":
            return None
        name = (settings.seed_default_admin_name or "Default Admin").strip()
        user = await self.user_repository.get_by_workspace_email(workspace.id, email)
        if user is None:
            return await self.user_repository.create(
                User(
                    workspace_id=workspace.id,
                    email=email,
                    name=name,
                    role=UserRole.ADMIN.value,
                )
            )
        user.name = name
        user.role = UserRole.ADMIN.value
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def seed_symbols(self) -> list[Symbol]:
        symbols: list[Symbol] = []
        for payload in DEFAULT_SYMBOLS:
            values = payload.model_dump(mode="python")
            symbol = await self.symbol_repository.get_by_symbol(payload.symbol)
            if symbol is None:
                symbol = await self.symbol_repository.create(Symbol(**values))
            else:
                for field_name, field_value in values.items():
                    setattr(symbol, field_name, field_value)
            symbols.append(symbol)
        await self.session.flush()
        return symbols

    async def seed_data_sources(self, workspace: Workspace | None) -> list[DataSource]:
        if workspace is None:
            return []
        data_sources: list[DataSource] = []
        for payload in default_data_sources(workspace.id):
            values = payload.model_dump(mode="python")
            data_source = await self.data_source_repository.get_by_natural_key(
                workspace_id=payload.workspace_id,
                name=payload.name,
                provider=payload.provider,
                source_type=payload.source_type.value,
            )
            if data_source is None:
                data_source = await self.data_source_repository.create(DataSource(**values))
            else:
                data_source.status = payload.status.value
                data_source.config_json = payload.config_json
            data_sources.append(data_source)
        await self.session.flush()
        return data_sources
