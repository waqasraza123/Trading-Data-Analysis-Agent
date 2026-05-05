from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_sources.models import DataSource
from app.modules.market_scans.models import ScheduledScanConfig
from app.modules.provider_credentials.models import ProviderCredentialRef
from app.modules.scanner_presets.models import ScannerPreset
from app.modules.symbols.models import Symbol
from app.modules.users.models import User
from app.modules.workspace_setup.models import WorkspaceSetupRun, WorkspaceSetupStepResult
from app.modules.workspaces.models import Workspace


class WorkspaceSetupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: WorkspaceSetupRun) -> WorkspaceSetupRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, setup_run_id: UUID) -> WorkspaceSetupRun | None:
        return await self.session.get(WorkspaceSetupRun, setup_run_id)

    async def create_step_result(
        self,
        step_result: WorkspaceSetupStepResult,
    ) -> WorkspaceSetupStepResult:
        self.session.add(step_result)
        await self.session.flush()
        await self.session.refresh(step_result)
        return step_result

    async def get_step_result(
        self,
        setup_run_id: UUID,
        step_key: str,
    ) -> WorkspaceSetupStepResult | None:
        statement: Select[tuple[WorkspaceSetupStepResult]] = select(WorkspaceSetupStepResult).where(
            WorkspaceSetupStepResult.setup_run_id == setup_run_id,
            WorkspaceSetupStepResult.step_key == step_key,
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_step_results(self, setup_run_id: UUID) -> list[WorkspaceSetupStepResult]:
        statement: Select[tuple[WorkspaceSetupStepResult]] = (
            select(WorkspaceSetupStepResult)
            .where(WorkspaceSetupStepResult.setup_run_id == setup_run_id)
            .order_by(WorkspaceSetupStepResult.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        return await self.session.get(Workspace, workspace_id)

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_symbol(self, symbol_id: UUID) -> Symbol | None:
        return await self.session.get(Symbol, symbol_id)

    async def get_symbols_by_codes(self, symbol_codes: list[str]) -> list[Symbol]:
        normalized = [symbol_code.strip().upper() for symbol_code in symbol_codes if symbol_code]
        if not normalized:
            return []
        result = await self.session.execute(
            select(Symbol).where(Symbol.symbol.in_(normalized), Symbol.is_active.is_(True))
        )
        symbols = list(result.scalars().all())
        by_code = {symbol.symbol: symbol for symbol in symbols}
        return [by_code[symbol_code] for symbol_code in normalized if symbol_code in by_code]

    async def get_data_source(self, data_source_id: UUID) -> DataSource | None:
        return await self.session.get(DataSource, data_source_id)

    async def get_credential_ref(
        self,
        credential_ref_id: UUID,
    ) -> ProviderCredentialRef | None:
        return await self.session.get(ProviderCredentialRef, credential_ref_id)

    async def get_scanner_preset(self, preset_id: UUID) -> ScannerPreset | None:
        return await self.session.get(ScannerPreset, preset_id)

    async def get_scan_config(self, scan_config_id: UUID) -> ScheduledScanConfig | None:
        return await self.session.get(ScheduledScanConfig, scan_config_id)
