from datetime import datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.read_models.builders import ReadModelBuilder
from app.modules.read_models.models import (
    CommandCenterReadModel,
    DashboardSymbolReadModel,
    SignalCardReadModel,
)
from app.modules.read_models.repository import ReadModelRepository
from app.modules.read_models.schemas import (
    DashboardSymbolReadModelFilters,
    SignalCardReadModelFilters,
)


class ReadModelService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = ReadModelRepository(session)
        self.builder = ReadModelBuilder()

    async def rebuild_symbol_read_model(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        source_id: UUID | None = None,
    ) -> DashboardSymbolReadModel:
        try:
            await self.validate_workspace(workspace_id)
            await self.validate_symbol(symbol_id)
            artifacts = await self.repository.load_symbol_artifacts(
                workspace_id=workspace_id,
                symbol_id=symbol_id,
                timeframe=timeframe,
                source_id=source_id,
                market_memory_version=self.settings.market_memory_state_version,
            )
            model = self.builder.build_symbol_model(
                artifacts=artifacts,
                read_model_version=self.settings.read_model_version,
            )
            existing = await self.repository.get_symbol_read_model(
                workspace_id=workspace_id,
                symbol_id=symbol_id,
                source_id=source_id,
                timeframe=timeframe,
                read_model_version=self.settings.read_model_version,
            )
            persisted = await self.repository.upsert_symbol_model(model, existing)
            await self.session.commit()
            await self.session.refresh(persisted)
            return persisted
        except AppError:
            await self.session.rollback()
            raise
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "dashboard_symbol_read_model_conflict",
                "Dashboard symbol read model could not be persisted",
            ) from error
        except Exception:
            await self.session.rollback()
            raise

    async def rebuild_signal_card(self, signal_id: UUID) -> SignalCardReadModel:
        try:
            signal = await self.repository.get_signal(signal_id)
            if signal is None:
                raise AppError(404, "signal_not_found", "Signal not found")
            artifacts = await self.repository.load_signal_artifacts(
                signal=signal,
                market_memory_version=self.settings.market_memory_state_version,
            )
            model = self.builder.build_signal_card(
                artifacts=artifacts,
                read_model_version=self.settings.read_model_version,
            )
            existing = await self.repository.get_signal_card(
                signal_id=signal.id,
                read_model_version=self.settings.read_model_version,
            )
            persisted = await self.repository.upsert_signal_card(model, existing)
            await self.session.commit()
            await self.session.refresh(persisted)
            return persisted
        except AppError:
            await self.session.rollback()
            raise
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "signal_card_read_model_conflict",
                "Signal card read model could not be persisted",
            ) from error
        except Exception:
            await self.session.rollback()
            raise

    async def rebuild_workspace_signal_cards(
        self,
        workspace_id: UUID,
        limit: int = 500,
    ) -> tuple[list[SignalCardReadModel], int]:
        await self.validate_workspace(workspace_id)
        bounded_limit = min(limit, self.settings.read_model_max_limit)
        signals = await self.repository.list_recent_signals(workspace_id, bounded_limit)
        cards: list[SignalCardReadModel] = []
        skipped_count = 0
        for signal in signals:
            try:
                cards.append(await self.rebuild_signal_card(signal.id))
            except AppError:
                skipped_count += 1
        return cards, skipped_count

    async def rebuild_command_center(
        self,
        workspace_id: UUID,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> CommandCenterReadModel:
        try:
            await self.validate_workspace(workspace_id)
            artifacts = await self.repository.load_command_center_artifacts(
                workspace_id=workspace_id,
                read_model_version=self.settings.read_model_version,
                limit=self.settings.read_model_default_limit,
            )
            model = self.builder.build_command_center_model(
                artifacts=artifacts,
                read_model_version=self.settings.read_model_version,
                period_start=period_start,
                period_end=period_end,
            )
            persisted = await self.repository.create_command_center_model(model)
            await self.session.commit()
            await self.session.refresh(persisted)
            return persisted
        except AppError:
            await self.session.rollback()
            raise
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "command_center_read_model_conflict",
                "Command center read model could not be persisted",
            ) from error
        except Exception:
            await self.session.rollback()
            raise

    async def get_dashboard_symbols(
        self,
        filters: DashboardSymbolReadModelFilters,
    ) -> list[DashboardSymbolReadModel]:
        await self.validate_workspace(filters.workspace_id)
        normalized_filters = filters.model_copy(
            update={"limit": min(filters.limit, self.settings.read_model_max_limit)}
        )
        return await self.repository.list_symbol_read_models(
            filters=normalized_filters,
            read_model_version=self.settings.read_model_version,
        )

    async def get_signal_cards(
        self,
        filters: SignalCardReadModelFilters,
    ) -> list[SignalCardReadModel]:
        await self.validate_workspace(filters.workspace_id)
        normalized_filters = filters.model_copy(
            update={"limit": min(filters.limit, self.settings.read_model_max_limit)}
        )
        return await self.repository.list_signal_cards(
            filters=normalized_filters,
            read_model_version=self.settings.read_model_version,
        )

    async def get_command_center(self, workspace_id: UUID) -> CommandCenterReadModel:
        await self.validate_workspace(workspace_id)
        model = await self.repository.get_latest_command_center_model(
            workspace_id=workspace_id,
            read_model_version=self.settings.read_model_version,
        )
        if model is None:
            raise AppError(
                404, "command_center_read_model_not_found", "Command center read model not found"
            )
        return model

    async def validate_workspace(self, workspace_id: UUID) -> None:
        workspace = await self.repository.get_workspace(workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")

    async def validate_symbol(self, symbol_id: UUID) -> None:
        symbol = await self.repository.get_symbol(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
