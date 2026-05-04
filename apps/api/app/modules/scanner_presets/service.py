import logging
from datetime import timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.candles.timeframes import Timeframe
from app.modules.market_scans.models import (
    MarketWatchlist,
    MarketWatchlistItem,
    MarketWatchlistStatus,
    ScheduledScanConfig,
    ScheduledScanConfigStatus,
    ScheduledScanMode,
)
from app.modules.market_scans.repository import MarketScanRepository
from app.modules.market_scans.service import MarketScanService
from app.modules.scanner_presets.models import (
    ScannerPreset,
    ScannerPresetApplication,
    ScannerPresetApplicationStatus,
    ScannerPresetCategory,
    ScannerPresetStatus,
)
from app.modules.scanner_presets.repository import ScannerPresetRepository
from app.modules.scanner_presets.schemas import ScannerPresetApplyRequest
from app.modules.scanner_presets.seed import default_scanner_presets
from app.modules.symbols.models import Symbol

logger = logging.getLogger(__name__)


class ScannerPresetService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        repository: ScannerPresetRepository | None = None,
        market_scan_repository: MarketScanRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or ScannerPresetRepository(session)
        self.market_scan_repository = market_scan_repository or MarketScanRepository(session)
        self.market_scan_service = MarketScanService(
            session,
            settings=self.settings,
            repository=self.market_scan_repository,
        )

    async def seed_default_presets(self, commit: bool = True) -> list[ScannerPreset]:
        seeded: list[ScannerPreset] = []
        for definition in default_scanner_presets(self.settings.scanner_preset_version):
            existing = await self.repository.get_by_key_version(
                definition.key,
                definition.preset_version,
                workspace_id=None,
            )
            if existing is None:
                seeded.append(await self.repository.create_preset(definition))
                continue
            update_preset(existing, definition)
            seeded.append(existing)
        await self.session.flush()
        if commit:
            await self.session.commit()
        return seeded

    async def list_presets(
        self,
        workspace_id: UUID | None = None,
        category: ScannerPresetCategory | None = None,
    ) -> list[ScannerPreset]:
        return await self.repository.list_presets(
            workspace_id=workspace_id,
            category=category.value if category is not None else None,
            status=ScannerPresetStatus.ACTIVE.value,
        )

    async def get_preset(self, key: str, workspace_id: UUID | None = None) -> ScannerPreset:
        preset = await self.repository.get_active_by_key(
            key=key,
            preset_version=self.settings.scanner_preset_version,
            workspace_id=workspace_id,
        )
        if preset is None:
            raise AppError(404, "scanner_preset_not_found", "Scanner preset not found")
        return preset

    async def get_application(self, application_id: UUID) -> ScannerPresetApplication:
        application = await self.repository.get_application(application_id)
        if application is None:
            raise AppError(
                404,
                "scanner_preset_application_not_found",
                "Scanner preset application not found",
            )
        return application

    async def apply_preset(
        self,
        workspace_id: UUID,
        preset_id: UUID,
        options: ScannerPresetApplyRequest,
    ) -> ScannerPresetApplication:
        if workspace_id != options.workspace_id:
            raise AppError(422, "workspace_mismatch", "Workspace path and request do not match")
        preset = await self.repository.get_preset_by_id(preset_id)
        if preset is None or preset.status != ScannerPresetStatus.ACTIVE.value:
            raise AppError(404, "scanner_preset_not_found", "Scanner preset not found")
        await self.validate_application_inputs(preset, options)
        warnings: list[str] = []
        symbols = await self.resolve_symbols(preset, options, warnings)
        timeframes = resolve_timeframes(preset, options)
        if not symbols:
            warnings.append("No active symbols matched the selected symbols or preset templates.")
        watchlist: MarketWatchlist | None = None
        scan_config: ScheduledScanConfig | None = None
        try:
            if options.create_watchlist:
                watchlist = await self.create_watchlist_from_preset(
                    preset=preset,
                    options=options,
                    symbols=symbols,
                    timeframes=timeframes,
                )
            elif symbols:
                warnings.append("Watchlist creation was skipped by request.")
            if options.create_scan_config:
                scan_config = await self.create_scan_config_from_preset(
                    preset=preset,
                    options=options,
                    watchlist=watchlist,
                    symbols=symbols,
                    timeframes=timeframes,
                    warnings=warnings,
                )
            else:
                warnings.append("Scan config creation was skipped by request.")
            if not options.create_watchlist and not options.create_scan_config:
                warnings.append("No watchlist or scan config was requested.")
            application = ScannerPresetApplication(
                workspace_id=workspace_id,
                scanner_preset_id=preset.id,
                status=(
                    ScannerPresetApplicationStatus.COMPLETED_WITH_WARNINGS.value
                    if warnings
                    else ScannerPresetApplicationStatus.COMPLETED.value
                ),
                watchlist_id=watchlist.id if watchlist is not None else None,
                scan_config_id=scan_config.id if scan_config is not None else None,
                preference_profile_id=options.preference_profile_id,
                applied_config_json=build_application_config(
                    preset=preset,
                    options=options,
                    symbols=symbols,
                    timeframes=timeframes,
                    warnings=warnings,
                ),
                error_message=None,
            )
            created_application = await self.repository.create_application(application)
            await self.session.commit()
            logger.info(
                "scanner_preset_applied",
                extra={
                    "application_id": str(created_application.id),
                    "preset_id": str(preset.id),
                    "workspace_id": str(workspace_id),
                    "status": created_application.status,
                },
            )
            return created_application
        except IntegrityError as error:
            await self.session.rollback()
            failed = await self.record_failed_application(
                workspace_id=workspace_id,
                preset_id=preset.id,
                options=options,
                error_message="Scanner preset could not be applied.",
            )
            raise AppError(
                409,
                "scanner_preset_application_conflict",
                failed.error_message or "Scanner preset could not be applied",
            ) from error

    async def validate_application_inputs(
        self,
        preset: ScannerPreset,
        options: ScannerPresetApplyRequest,
    ) -> None:
        workspace = await self.repository.get_workspace(options.workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")
        if preset.workspace_id is not None and preset.workspace_id != options.workspace_id:
            raise AppError(422, "workspace_preset_mismatch", "Preset does not belong to workspace")
        await self.market_scan_service.validate_optional_source(
            workspace_id=options.workspace_id,
            source_id=options.source_id,
        )
        if options.preference_profile_id is None:
            return
        profile = await self.repository.get_preference_profile(options.preference_profile_id)
        if profile is None:
            raise AppError(404, "preference_profile_not_found", "Preference profile not found")
        if profile.workspace_id != options.workspace_id:
            raise AppError(
                422,
                "workspace_preference_profile_mismatch",
                "Preference profile does not belong to workspace",
            )

    async def resolve_symbols(
        self,
        preset: ScannerPreset,
        options: ScannerPresetApplyRequest,
        warnings: list[str],
    ) -> list[Symbol]:
        if options.symbol_ids:
            symbols = await self.repository.get_symbols_by_ids(options.symbol_ids)
            if len(symbols) != len(options.symbol_ids):
                found_ids = {symbol.id for symbol in symbols}
                missing_ids = [
                    str(symbol_id) for symbol_id in options.symbol_ids if symbol_id not in found_ids
                ]
                raise AppError(
                    422,
                    "invalid_selected_symbols",
                    f"Selected symbols are unavailable or inactive: {', '.join(missing_ids)}",
                )
            return symbols
        symbol_codes = extract_symbol_template_codes(preset.symbol_templates_json)
        symbols = await self.repository.get_symbols_by_codes(symbol_codes)
        missing_codes = sorted(set(symbol_codes) - {symbol.symbol for symbol in symbols})
        if missing_codes:
            warnings.append(
                "Preset symbol templates were skipped because symbols do not exist: "
                f"{', '.join(missing_codes)}."
            )
        return symbols

    async def create_watchlist_from_preset(
        self,
        *,
        preset: ScannerPreset,
        options: ScannerPresetApplyRequest,
        symbols: list[Symbol],
        timeframes: list[str],
    ) -> MarketWatchlist:
        watchlist = MarketWatchlist(
            workspace_id=options.workspace_id,
            name=watchlist_name(preset, options),
            description=preset.description,
            status=MarketWatchlistStatus.ACTIVE.value,
            metadata_json={
                "scannerPresetId": str(preset.id),
                "scannerPresetKey": preset.key,
                "scannerPresetVersion": preset.preset_version,
                "doesNotRunScans": True,
            },
        )
        created = await self.market_scan_repository.create_watchlist(watchlist)
        include_partial = bool(
            read_template_value(
                preset.watchlist_template_json,
                "includePartialLiveCandle",
                False,
            )
        )
        item_metadata = read_template_value(preset.watchlist_template_json, "itemMetadata", {})
        metadata_json = item_metadata if isinstance(item_metadata, dict) else {}
        for symbol in symbols:
            for timeframe in timeframes:
                await self.market_scan_service.validate_symbol_and_optional_source(
                    workspace_id=options.workspace_id,
                    symbol_id=symbol.id,
                    source_id=options.source_id,
                )
                await self.market_scan_repository.create_watchlist_item(
                    MarketWatchlistItem(
                        workspace_id=options.workspace_id,
                        watchlist_id=created.id,
                        symbol_id=symbol.id,
                        source_id=options.source_id,
                        timeframe=timeframe,
                        include_partial_live_candle=include_partial,
                        is_active=True,
                        metadata_json={
                            **metadata_json,
                            "scannerPresetId": str(preset.id),
                            "scannerPresetKey": preset.key,
                        },
                    )
                )
        return created

    async def create_scan_config_from_preset(
        self,
        *,
        preset: ScannerPreset,
        options: ScannerPresetApplyRequest,
        watchlist: MarketWatchlist | None,
        symbols: list[Symbol],
        timeframes: list[str],
        warnings: list[str],
    ) -> ScheduledScanConfig | None:
        template = preset.scan_config_template_json
        lookback_minutes = int(
            read_template_value(
                template,
                "lookbackMinutes",
                self.settings.market_scan_default_lookback_minutes,
            )
        )
        interval_seconds = int(
            read_template_value(
                template,
                "intervalSeconds",
                self.settings.market_scan_default_interval_seconds,
            )
        )
        scan_mode = (
            ScheduledScanMode.WATCHLIST
            if watchlist is not None
            else ScheduledScanMode.SINGLE_SYMBOL
        )
        symbol_id: UUID | None = None
        timeframe: str | None = None
        if scan_mode == ScheduledScanMode.SINGLE_SYMBOL:
            if not symbols or not timeframes:
                warnings.append("Scan config was not created because no scan target was available.")
                return None
            symbol_id = symbols[0].id
            timeframe = timeframes[0]
            if len(symbols) > 1 or len(timeframes) > 1:
                warnings.append(
                    "Single-symbol scan config used the first resolved symbol and timeframe "
                    "because no watchlist was created."
                )
        await self.market_scan_service.validate_scan_config_fields(
            workspace_id=options.workspace_id,
            scan_mode=scan_mode,
            watchlist_id=watchlist.id if watchlist is not None else None,
            symbol_id=symbol_id,
            source_id=options.source_id,
            timeframe=timeframe,
        )
        scan_config = ScheduledScanConfig(
            workspace_id=options.workspace_id,
            name=scan_config_name(preset, options),
            description=preset.description,
            watchlist_id=watchlist.id if watchlist is not None else None,
            symbol_id=symbol_id,
            source_id=options.source_id,
            timeframe=timeframe,
            scan_mode=scan_mode.value,
            lookback_minutes=lookback_minutes,
            interval_seconds=interval_seconds,
            include_partial_live_candle=bool(
                read_template_value(template, "includePartialLiveCandle", False)
            ),
            include_news_correlation=bool(
                read_template_value(template, "includeNewsCorrelation", False)
            ),
            include_ai_explanation=bool(
                read_template_value(template, "includeAiExplanation", False)
            ),
            include_reasoning=bool(read_template_value(template, "includeReasoning", False)),
            include_action_plan=bool(read_template_value(template, "includeActionPlan", False)),
            status=ScheduledScanConfigStatus.ACTIVE.value,
            next_run_at=(utc_now() + timedelta(seconds=interval_seconds)).replace(microsecond=0),
            metadata_json={
                "scannerPresetId": str(preset.id),
                "scannerPresetKey": preset.key,
                "scannerPresetVersion": preset.preset_version,
                "doesNotRunOnApply": True,
                "operatorMustRunExplicitlyForImmediateScan": True,
            },
        )
        return await self.market_scan_repository.create_scan_config(scan_config)

    async def record_failed_application(
        self,
        *,
        workspace_id: UUID,
        preset_id: UUID,
        options: ScannerPresetApplyRequest,
        error_message: str,
    ) -> ScannerPresetApplication:
        application = ScannerPresetApplication(
            workspace_id=workspace_id,
            scanner_preset_id=preset_id,
            status=ScannerPresetApplicationStatus.FAILED.value,
            watchlist_id=None,
            scan_config_id=None,
            preference_profile_id=options.preference_profile_id,
            applied_config_json={
                "request": options.model_dump(mode="json"),
                "doesNotRunScans": True,
            },
            error_message=error_message,
        )
        created = await self.repository.create_application(application)
        await self.session.commit()
        return created


def update_preset(existing: ScannerPreset, definition: ScannerPreset) -> None:
    existing.name = definition.name
    existing.description = definition.description
    existing.category = definition.category
    existing.status = definition.status
    existing.market_types_json = definition.market_types_json
    existing.symbol_templates_json = definition.symbol_templates_json
    existing.timeframe_templates_json = definition.timeframe_templates_json
    existing.session_filters_json = definition.session_filters_json
    existing.scan_config_template_json = definition.scan_config_template_json
    existing.watchlist_template_json = definition.watchlist_template_json
    existing.preference_profile_filters_json = definition.preference_profile_filters_json
    existing.metadata_json = definition.metadata_json


def extract_symbol_template_codes(templates: list[dict[str, object]]) -> list[str]:
    codes: list[str] = []
    for template in templates:
        raw_symbol = template.get("symbol")
        if isinstance(raw_symbol, str) and raw_symbol.strip():
            codes.append(raw_symbol.strip().upper())
        raw_symbols = template.get("symbols")
        if isinstance(raw_symbols, list):
            codes.extend(str(item).strip().upper() for item in raw_symbols if str(item).strip())
    return list(dict.fromkeys(codes))


def resolve_timeframes(preset: ScannerPreset, options: ScannerPresetApplyRequest) -> list[str]:
    raw_timeframes = (
        [item.value for item in options.timeframes]
        if options.timeframes
        else preset.timeframe_templates_json
    )
    timeframes: list[str] = []
    for raw_timeframe in raw_timeframes:
        timeframe = Timeframe(str(raw_timeframe)).value
        if timeframe not in timeframes:
            timeframes.append(timeframe)
    return timeframes


def watchlist_name(preset: ScannerPreset, options: ScannerPresetApplyRequest) -> str:
    base_name = options.name_override or preset.name
    return truncate_name(f"{base_name} watchlist")


def scan_config_name(preset: ScannerPreset, options: ScannerPresetApplyRequest) -> str:
    base_name = options.name_override or preset.name
    return truncate_name(f"{base_name} scan")


def truncate_name(value: str) -> str:
    return value[:160].rstrip()


def read_template_value(
    template: dict[str, object],
    camel_key: str,
    fallback: object,
) -> object:
    snake_key = camel_to_snake(camel_key)
    return template.get(camel_key, template.get(snake_key, fallback))


def camel_to_snake(value: str) -> str:
    output: list[str] = []
    for char in value:
        if char.isupper():
            output.append("_")
            output.append(char.lower())
        else:
            output.append(char)
    return "".join(output).lstrip("_")


def build_application_config(
    *,
    preset: ScannerPreset,
    options: ScannerPresetApplyRequest,
    symbols: list[Symbol],
    timeframes: list[str],
    warnings: list[str],
) -> dict[str, object]:
    return {
        "presetKey": preset.key,
        "presetVersion": preset.preset_version,
        "request": options.model_dump(mode="json"),
        "resolvedSymbolIds": [str(symbol.id) for symbol in symbols],
        "resolvedSymbols": [symbol.symbol for symbol in symbols],
        "resolvedTimeframes": timeframes,
        "warnings": warnings,
        "doesNotRunScans": True,
        "doesNotCreateSetups": True,
    }
