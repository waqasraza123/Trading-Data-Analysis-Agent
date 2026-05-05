from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.candles.normalizer import RawCandlePayload
from app.modules.candles.timeframes import Timeframe
from app.modules.data_sources.models import DataSourceStatus, DataSourceType
from app.modules.data_sources.schemas import DataSourceCreate, DataSourceUpdate
from app.modules.data_sources.service import DataSourceService
from app.modules.imports.schemas import JsonCandleImportRequest
from app.modules.imports.service import ImportService
from app.modules.market_scans.scanner import MarketScanExecutor
from app.modules.market_scans.schemas import (
    WatchlistCreate,
    WatchlistItemCreate,
)
from app.modules.market_scans.service import MarketScanService
from app.modules.preference_profiles.schemas import PreferenceProfileCreate
from app.modules.preference_profiles.service import PreferenceProfileService
from app.modules.product_readiness.repository import ProductReadinessRepository
from app.modules.product_readiness.service import ProductReadinessService
from app.modules.provider_credentials.models import (
    ProviderCredentialStatus,
)
from app.modules.provider_credentials.schemas import ProviderCredentialRefCreate
from app.modules.provider_credentials.service import ProviderCredentialService
from app.modules.scanner_presets.schemas import ScannerPresetApplyRequest
from app.modules.scanner_presets.service import ScannerPresetService
from app.modules.symbols.models import MarketType
from app.modules.symbols.schemas import SymbolCreate
from app.modules.symbols.service import SymbolService
from app.modules.synthetic_fixtures.generator import SyntheticFixtureGenerator
from app.modules.synthetic_fixtures.schemas import (
    SyntheticFixtureGenerateRequest,
    SyntheticFixturePattern,
    SyntheticVolumeBehavior,
)
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService
from app.modules.workspace_setup.models import WorkspaceSetupRun, WorkspaceSetupStepResult
from app.modules.workspace_setup.repository import WorkspaceSetupRepository
from app.modules.workspace_setup.schemas import (
    CredentialReferenceStepInput,
    DataSourceStepInput,
    DemoDataStepInput,
    FirstScanStepInput,
    PreferenceProfileStepInput,
    ReadinessCheckStepInput,
    ScannerPresetStepInput,
    SymbolsStepInput,
    UserStepInput,
    WatchlistStepInput,
    WorkspaceSetupDemoWorkspaceRequest,
    WorkspaceSetupDemoWorkspaceResponse,
    WorkspaceSetupRunRead,
    WorkspaceSetupStartRequest,
    WorkspaceStepInput,
)
from app.modules.workspace_setup.steps import (
    OPTIONAL_SETUP_STEPS,
    SETUP_STEP_ORDER,
    WorkspaceSetupStatus,
    WorkspaceSetupStepKey,
    WorkspaceSetupStepStatus,
    next_step_after,
)
from app.modules.workspaces.schemas import WorkspaceCreate
from app.modules.workspaces.service import WorkspaceService


class WorkspaceSetupService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = WorkspaceSetupRepository(session)

    async def start_setup(self, payload: WorkspaceSetupStartRequest) -> WorkspaceSetupRunRead:
        workspace_id = payload.workspace_id
        user_id = payload.user_id
        if workspace_id is not None and await self.repository.get_workspace(workspace_id) is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")
        if user_id is not None:
            user = await self.repository.get_user(user_id)
            if user is None:
                raise AppError(404, "user_not_found", "User not found")
            if workspace_id is not None and user.workspace_id != workspace_id:
                raise AppError(422, "workspace_user_mismatch", "User does not belong to workspace")
        run = WorkspaceSetupRun(
            workspace_id=workspace_id,
            user_id=user_id,
            status=WorkspaceSetupStatus.DRAFT.value,
            setup_version=self.settings.workspace_setup_version,
            current_step=WorkspaceSetupStepKey.WORKSPACE.value,
            completed_steps_json=[],
            skipped_steps_json=[],
            failed_steps_json=[],
            result_json={
                "initialContext": payload.initial_context_json,
                "safety": safety_payload(),
            },
        )
        try:
            created = await self.repository.create_run(run)
            for step in SETUP_STEP_ORDER:
                await self.repository.create_step_result(
                    WorkspaceSetupStepResult(
                        setup_run_id=created.id,
                        step_key=step.value,
                        status=WorkspaceSetupStepStatus.PENDING.value,
                        input_json={},
                        output_json=None,
                    )
                )
            await self.session.commit()
            return await self.get_setup_run(created.id)
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409, "workspace_setup_conflict", "Setup run could not be created"
            ) from error

    async def get_setup_run(self, setup_run_id: UUID) -> WorkspaceSetupRunRead:
        run = await self.load_run(setup_run_id)
        steps = await self.repository.list_step_results(run.id)
        return WorkspaceSetupRunRead.model_validate(
            {
                **run.__dict__,
                "step_results": steps,
            }
        )

    async def complete_step(
        self,
        setup_run_id: UUID,
        step_key: WorkspaceSetupStepKey,
        input_json: dict[str, object],
    ) -> WorkspaceSetupRunRead:
        run = await self.load_run(setup_run_id)
        if run.status in terminal_statuses():
            raise AppError(409, "workspace_setup_closed", "Setup run is already closed")
        parsed_input = parse_step_input(step_key, input_json)
        step_result = await self.load_step_result(run.id, step_key)
        try:
            output = await self.execute_step(run, step_key, parsed_input)
            step_result.status = WorkspaceSetupStepStatus.COMPLETED.value
            step_result.input_json = sanitize_input(step_key, input_json)
            step_result.output_json = output
            step_result.error_message = None
            mark_step_complete(run, step_key)
            self.update_run_progress(run)
            await self.session.commit()
            return await self.get_setup_run(run.id)
        except AppError as error:
            await self.session.rollback()
            run = await self.load_run(setup_run_id)
            step_result = await self.load_step_result(run.id, step_key)
            step_result.status = WorkspaceSetupStepStatus.FAILED.value
            step_result.input_json = sanitize_input(step_key, input_json)
            step_result.output_json = None
            step_result.error_message = error.message
            mark_step_failed(run, step_key)
            run.status = WorkspaceSetupStatus.FAILED.value
            run.error_message = error.message
            await self.session.commit()
            raise

    async def skip_step(
        self,
        setup_run_id: UUID,
        step_key: WorkspaceSetupStepKey,
    ) -> WorkspaceSetupRunRead:
        run = await self.load_run(setup_run_id)
        if step_key not in OPTIONAL_SETUP_STEPS:
            raise AppError(
                422, "workspace_setup_step_required", "This setup step cannot be skipped"
            )
        step_result = await self.load_step_result(run.id, step_key)
        step_result.status = WorkspaceSetupStepStatus.SKIPPED.value
        step_result.input_json = {}
        step_result.output_json = {"skipped": True}
        step_result.error_message = None
        mark_step_skipped(run, step_key)
        self.update_run_progress(run)
        await self.session.commit()
        return await self.get_setup_run(run.id)

    async def finish_setup(self, setup_run_id: UUID) -> WorkspaceSetupRunRead:
        run = await self.load_run(setup_run_id)
        if run.status in terminal_statuses():
            return await self.get_setup_run(run.id)
        if WorkspaceSetupStepKey.READINESS_CHECK.value not in run.completed_steps_json:
            try:
                output = await self.run_readiness_check(run, ReadinessCheckStepInput(run=True))
                step_result = await self.load_step_result(
                    run.id, WorkspaceSetupStepKey.READINESS_CHECK
                )
                step_result.status = WorkspaceSetupStepStatus.COMPLETED.value
                step_result.input_json = {"run": True}
                step_result.output_json = output
                mark_step_complete(run, WorkspaceSetupStepKey.READINESS_CHECK)
            except AppError:
                mark_step_failed(run, WorkspaceSetupStepKey.READINESS_CHECK)
        failed_required = [
            step
            for step in run.failed_steps_json
            if WorkspaceSetupStepKey(step) not in OPTIONAL_SETUP_STEPS
        ]
        if failed_required:
            run.status = WorkspaceSetupStatus.FAILED.value
        elif run.failed_steps_json:
            run.status = WorkspaceSetupStatus.COMPLETED_WITH_WARNINGS.value
        else:
            readiness = (
                run.result_json.get("readiness") if isinstance(run.result_json, dict) else None
            )
            readiness_label = (
                readiness.get("readinessLabel") if isinstance(readiness, dict) else None
            )
            run.status = (
                WorkspaceSetupStatus.COMPLETED.value
                if readiness_label in {None, "ready"}
                else WorkspaceSetupStatus.COMPLETED_WITH_WARNINGS.value
            )
        run.current_step = WorkspaceSetupStepKey.FIRST_SCAN.value
        run.completed_at = utc_now()
        await self.session.commit()
        return await self.get_setup_run(run.id)

    async def create_demo_workspace(
        self,
        payload: WorkspaceSetupDemoWorkspaceRequest,
    ) -> WorkspaceSetupDemoWorkspaceResponse:
        run = await self.start_setup(
            WorkspaceSetupStartRequest(initial_context_json={"demo": True})
        )
        await self.complete_step(
            run.id,
            WorkspaceSetupStepKey.WORKSPACE,
            {"mode": "create", "name": payload.workspace_name},
        )
        run = await self.get_setup_run(run.id)
        await self.complete_step(
            run.id,
            WorkspaceSetupStepKey.USER,
            {
                "mode": "create",
                "email": payload.operator_email,
                "name": payload.operator_name,
                "role": "analyst",
            },
        )
        await self.complete_step(
            run.id,
            WorkspaceSetupStepKey.SYMBOLS,
            {
                "marketType": payload.market_type.value,
                "symbolCodes": payload.symbol_codes,
                "createMissingSymbols": False,
            },
        )
        await self.complete_step(
            run.id,
            WorkspaceSetupStepKey.DATA_SOURCE,
            {
                "mode": "create",
                "sourceType": "mock",
                "name": "demo_synthetic",
                "provider": "mock",
                "configJson": {"demo": True, "syntheticFixtures": True},
            },
        )
        run = await self.get_setup_run(run.id)
        symbol_ids = list(run.result_json.get("symbolIds", []))
        source_id = run.result_json.get("dataSourceId")
        await self.complete_step(
            run.id,
            WorkspaceSetupStepKey.WATCHLIST,
            {
                "mode": "create",
                "name": "Demo market review",
                "description": "Stored synthetic demo market data review.",
                "symbolIds": symbol_ids,
                "sourceId": source_id,
                "timeframes": [timeframe.value for timeframe in payload.timeframes],
            },
        )
        if payload.seed_demo_data:
            await self.complete_step(
                run.id,
                WorkspaceSetupStepKey.DEMO_DATA,
                {
                    "enabled": True,
                    "symbolIds": symbol_ids,
                    "sourceId": source_id,
                    "timeframes": [timeframe.value for timeframe in payload.timeframes],
                    "candleCount": 180,
                    "pattern": "crypto_tick_sample",
                },
            )
        else:
            await self.skip_step(run.id, WorkspaceSetupStepKey.DEMO_DATA)
        await self.complete_step(run.id, WorkspaceSetupStepKey.READINESS_CHECK, {"run": True})
        finished = await self.finish_setup(run.id)
        return WorkspaceSetupDemoWorkspaceResponse(
            setup_run=finished,
            workspace_id=finished.workspace_id,
            user_id=finished.user_id,
            watchlist_id=uuid_or_none(finished.result_json.get("watchlistId")),
            scan_config_id=uuid_or_none(finished.result_json.get("scanConfigId")),
            readiness_run_id=uuid_or_none(finished.result_json.get("readinessRunId")),
        )

    async def execute_step(
        self,
        run: WorkspaceSetupRun,
        step_key: WorkspaceSetupStepKey,
        parsed_input: object,
    ) -> dict[str, object]:
        if step_key == WorkspaceSetupStepKey.WORKSPACE:
            return await self.setup_workspace(run, parsed_input)
        if step_key == WorkspaceSetupStepKey.USER:
            return await self.setup_user(run, parsed_input)
        if step_key == WorkspaceSetupStepKey.SYMBOLS:
            return await self.setup_symbols(run, parsed_input)
        if step_key == WorkspaceSetupStepKey.DATA_SOURCE:
            return await self.setup_data_source(run, parsed_input)
        if step_key == WorkspaceSetupStepKey.CREDENTIAL_REFERENCE:
            return await self.setup_credential_reference(run, parsed_input)
        if step_key == WorkspaceSetupStepKey.WATCHLIST:
            return await self.setup_watchlist(run, parsed_input)
        if step_key == WorkspaceSetupStepKey.SCANNER_PRESET:
            return await self.setup_scanner_preset(run, parsed_input)
        if step_key == WorkspaceSetupStepKey.PREFERENCE_PROFILE:
            return await self.setup_preference_profile(run, parsed_input)
        if step_key == WorkspaceSetupStepKey.DEMO_DATA:
            return await self.seed_demo_candles(run, parsed_input)
        if step_key == WorkspaceSetupStepKey.READINESS_CHECK:
            return await self.run_readiness_check(run, parsed_input)
        if step_key == WorkspaceSetupStepKey.FIRST_SCAN:
            return await self.run_first_scan(run, parsed_input)
        raise AppError(422, "workspace_setup_step_unknown", "Unknown setup step")

    async def setup_workspace(self, run: WorkspaceSetupRun, payload: object) -> dict[str, object]:
        assert isinstance(payload, WorkspaceStepInput)
        if payload.mode == "select":
            workspace = await self.repository.get_workspace(payload.workspace_id)  # type: ignore[arg-type]
            if workspace is None:
                raise AppError(404, "workspace_not_found", "Workspace not found")
        else:
            workspace = await WorkspaceService(self.session).create_workspace(
                WorkspaceCreate(name=payload.name or "Market Workspace")
            )
        run.workspace_id = workspace.id
        merge_result(run, {"workspaceId": str(workspace.id), "workspaceName": workspace.name})
        return {"workspaceId": str(workspace.id), "workspaceName": workspace.name}

    async def setup_user(self, run: WorkspaceSetupRun, payload: object) -> dict[str, object]:
        assert isinstance(payload, UserStepInput)
        workspace_id = require_run_workspace(run)
        if payload.mode == "select":
            user = await self.repository.get_user(payload.user_id)  # type: ignore[arg-type]
            if user is None or user.workspace_id != workspace_id:
                raise AppError(404, "user_not_found", "User not found for workspace")
        else:
            user = await UserService(self.session).create_user(
                UserCreate(
                    workspace_id=workspace_id,
                    email=payload.email or "operator@example.test",
                    name=payload.name or "Operator",
                    role=payload.role,
                )
            )
        run.user_id = user.id
        merge_result(run, {"userId": str(user.id), "userEmail": user.email, "userRole": user.role})
        return {"userId": str(user.id), "userEmail": user.email, "userRole": user.role}

    async def setup_symbols(self, run: WorkspaceSetupRun, payload: object) -> dict[str, object]:
        assert isinstance(payload, SymbolsStepInput)
        selected = []
        for symbol_id in payload.symbol_ids:
            symbol = await self.repository.get_symbol(symbol_id)
            if symbol is None or not symbol.is_active:
                raise AppError(404, "symbol_not_found", "Symbol not found")
            selected.append(symbol)
        found_by_code = await self.repository.get_symbols_by_codes(payload.symbol_codes)
        selected.extend(found_by_code)
        found_codes = {symbol.symbol for symbol in found_by_code}
        missing_codes = [code for code in payload.symbol_codes if code not in found_codes]
        if missing_codes and not payload.create_missing_symbols:
            raise AppError(
                422,
                "workspace_setup_symbols_missing",
                f"Symbols are not available: {', '.join(missing_codes)}",
            )
        for code in missing_codes:
            created = await SymbolService(self.session).create_symbol(
                build_symbol_create(code, payload.market_type)
            )
            selected.append(created)
        unique = {symbol.id: symbol for symbol in selected}
        symbol_ids = [str(symbol_id) for symbol_id in unique]
        merge_result(
            run,
            {
                "marketType": payload.market_type.value,
                "symbolIds": symbol_ids,
                "symbolCodes": [symbol.symbol for symbol in unique.values()],
            },
        )
        return {
            "marketType": payload.market_type.value,
            "symbolIds": symbol_ids,
            "symbolCodes": [symbol.symbol for symbol in unique.values()],
        }

    async def setup_data_source(self, run: WorkspaceSetupRun, payload: object) -> dict[str, object]:
        assert isinstance(payload, DataSourceStepInput)
        workspace_id = require_run_workspace(run)
        if payload.mode == "select":
            source = await self.repository.get_data_source(payload.data_source_id)  # type: ignore[arg-type]
            if source is None or source.workspace_id != workspace_id:
                raise AppError(404, "data_source_not_found", "Data source not found for workspace")
        else:
            source_type = normalize_source_type(payload.source_type)
            source = await DataSourceService(self.session).create_data_source(
                DataSourceCreate(
                    workspace_id=workspace_id,
                    name=payload.name or default_source_name(source_type),
                    source_type=source_type,
                    provider=payload.provider or default_provider(source_type),
                    status=DataSourceStatus.ACTIVE,
                    credential_ref_id=payload.credential_ref_id,
                    config_json=payload.config_json,
                )
            )
        merge_result(
            run,
            {
                "dataSourceId": str(source.id),
                "dataSourceType": source.source_type,
                "dataSourceProvider": source.provider,
            },
        )
        return {
            "dataSourceId": str(source.id),
            "sourceType": source.source_type,
            "provider": source.provider,
            "credentialRefId": str(source.credential_ref_id) if source.credential_ref_id else None,
        }

    async def setup_credential_reference(
        self,
        run: WorkspaceSetupRun,
        payload: object,
    ) -> dict[str, object]:
        assert isinstance(payload, CredentialReferenceStepInput)
        if payload.mode == "none":
            return {"credentialRequired": False}
        workspace_id = require_run_workspace(run)
        if payload.mode == "select":
            credential_ref = await self.repository.get_credential_ref(payload.credential_ref_id)  # type: ignore[arg-type]
            if credential_ref is None or credential_ref.workspace_id != workspace_id:
                raise AppError(
                    404,
                    "provider_credential_ref_not_found",
                    "Provider credential reference not found for workspace",
                )
        else:
            if payload.name is None or payload.provider is None:
                raise AppError(
                    422, "credential_ref_invalid", "Credential name and provider are required"
                )
            credential_ref = await ProviderCredentialService(
                self.session, self.settings
            ).create_credential_ref(
                ProviderCredentialRefCreate(
                    workspace_id=workspace_id,
                    name=payload.name,
                    provider=payload.provider,
                    credential_type=payload.credential_type,
                    status=ProviderCredentialStatus.ACTIVE,
                    secret_ref=payload.secret_ref,
                    public_metadata_json=payload.public_metadata_json,
                )
            )
        data_source_id = uuid_or_none(run.result_json.get("dataSourceId"))
        if data_source_id is not None:
            await DataSourceService(self.session).update_data_source(
                data_source_id,
                DataSourceUpdate(credential_ref_id=credential_ref.id),
            )
        merge_result(run, {"credentialRefId": str(credential_ref.id)})
        return {
            "credentialRefId": str(credential_ref.id),
            "provider": credential_ref.provider,
            "credentialType": credential_ref.credential_type,
            "secretRefConfigured": credential_ref.secret_ref is not None,
        }

    async def setup_watchlist(self, run: WorkspaceSetupRun, payload: object) -> dict[str, object]:
        assert isinstance(payload, WatchlistStepInput)
        workspace_id = require_run_workspace(run)
        scan_service = MarketScanService(self.session, settings=self.settings)
        if payload.mode == "select":
            watchlist = await scan_service.get_watchlist(payload.watchlist_id)  # type: ignore[arg-type]
            if watchlist.workspace_id != workspace_id:
                raise AppError(
                    422, "workspace_watchlist_mismatch", "Watchlist does not belong to workspace"
                )
            merge_result(run, {"watchlistId": str(watchlist.id)})
            return {"watchlistId": str(watchlist.id), "createdItemCount": 0}
        watchlist = await scan_service.create_watchlist(
            WatchlistCreate(
                workspace_id=workspace_id,
                name=payload.name or "Market review watchlist",
                description=payload.description,
                metadata_json={"createdBy": "workspace_setup"},
            )
        )
        created_count = 0
        for symbol_id in payload.symbol_ids:
            for timeframe in payload.timeframes:
                await scan_service.add_watchlist_item(
                    watchlist.id,
                    WatchlistItemCreate(
                        symbol_id=symbol_id,
                        source_id=payload.source_id,
                        timeframe=timeframe,
                        include_partial_live_candle=False,
                        metadata_json={"createdBy": "workspace_setup"},
                    ),
                )
                created_count += 1
        merge_result(run, {"watchlistId": str(watchlist.id)})
        return {"watchlistId": str(watchlist.id), "createdItemCount": created_count}

    async def setup_scanner_preset(
        self,
        run: WorkspaceSetupRun,
        payload: object,
    ) -> dict[str, object]:
        assert isinstance(payload, ScannerPresetStepInput)
        workspace_id = require_run_workspace(run)
        service = ScannerPresetService(self.session, self.settings)
        preset = (
            await self.repository.get_scanner_preset(payload.preset_id)
            if payload.preset_id is not None
            else await service.get_preset(payload.preset_key or "crypto_24h", workspace_id)
        )
        if preset is None:
            raise AppError(404, "scanner_preset_not_found", "Scanner preset not found")
        application = await service.apply_preset(
            workspace_id,
            preset.id,
            ScannerPresetApplyRequest(
                workspace_id=workspace_id,
                symbol_ids=payload.symbol_ids or result_uuid_list(run, "symbolIds"),
                source_id=payload.source_id or uuid_or_none(run.result_json.get("dataSourceId")),
                preference_profile_id=payload.preference_profile_id,
                timeframes=payload.timeframes or default_timeframes(self.settings),
                create_watchlist=payload.create_watchlist,
                create_scan_config=payload.create_scan_config,
                name_override=payload.name_override,
            ),
        )
        merge_result(
            run,
            {
                "scannerPresetApplicationId": str(application.id),
                "watchlistId": str(application.watchlist_id)
                if application.watchlist_id
                else run.result_json.get("watchlistId"),
                "scanConfigId": str(application.scan_config_id)
                if application.scan_config_id
                else run.result_json.get("scanConfigId"),
            },
        )
        return {
            "scannerPresetApplicationId": str(application.id),
            "status": application.status,
            "watchlistId": str(application.watchlist_id) if application.watchlist_id else None,
            "scanConfigId": str(application.scan_config_id) if application.scan_config_id else None,
        }

    async def setup_preference_profile(
        self,
        run: WorkspaceSetupRun,
        payload: object,
    ) -> dict[str, object]:
        assert isinstance(payload, PreferenceProfileStepInput)
        workspace_id = require_run_workspace(run)
        if payload.mode == "select":
            if payload.preference_profile_id is None:
                raise AppError(422, "preference_profile_required", "Preference profile is required")
            profile = await PreferenceProfileService(
                self.session, settings=self.settings
            ).get_preference_profile(payload.preference_profile_id)
            if profile.workspace_id != workspace_id:
                raise AppError(
                    422,
                    "workspace_preference_profile_mismatch",
                    "Preference profile does not belong to workspace",
                )
        else:
            profile = await PreferenceProfileService(
                self.session, settings=self.settings
            ).create_preference_profile(
                PreferenceProfileCreate(
                    workspace_id=workspace_id,
                    user_id=payload.user_id or run.user_id,
                    name=payload.name or "Default review preferences",
                    description=payload.description or "Workspace setup review preference profile.",
                    is_default=payload.is_default,
                    market_types_json=payload.market_types
                    or [
                        MarketType(
                            str(
                                run.result_json.get(
                                    "marketType", self.settings.workspace_setup_default_market
                                )
                            )
                        )
                    ],
                    symbol_ids_json=payload.symbol_ids or result_uuid_list(run, "symbolIds"),
                    timeframes_json=payload.timeframes or default_timeframes(self.settings),
                    require_fresh_data=payload.require_fresh_data,
                    require_timeframe_agreement=payload.require_timeframe_agreement,
                    require_acceptable_data_quality=payload.require_acceptable_data_quality,
                    minimum_confidence=payload.minimum_confidence,
                    minimum_setup_quality=payload.minimum_setup_quality,
                    metadata_json={"createdBy": "workspace_setup"},
                )
            )
        merge_result(run, {"preferenceProfileId": str(profile.id)})
        return {"preferenceProfileId": str(profile.id), "isDefault": profile.is_default}

    async def seed_demo_candles(self, run: WorkspaceSetupRun, payload: object) -> dict[str, object]:
        assert isinstance(payload, DemoDataStepInput)
        if not payload.enabled:
            return {"enabled": False, "importBatchIds": []}
        if not self.settings.workspace_setup_demo_data_enabled:
            raise AppError(
                403, "workspace_setup_demo_data_disabled", "Demo data seeding is disabled"
            )
        workspace_id = require_run_workspace(run)
        source_id = payload.source_id or uuid_or_none(run.result_json.get("dataSourceId"))
        if source_id is None:
            raise AppError(422, "data_source_required", "Demo data requires a data source")
        source = await self.repository.get_data_source(source_id)
        if source is None or source.workspace_id != workspace_id:
            raise AppError(404, "data_source_not_found", "Data source not found for workspace")
        if not source_is_demo_safe(source.source_type, source.provider, source.config_json):
            raise AppError(
                422,
                "workspace_setup_demo_source_required",
                "Demo candles require a demo, mock, or manual setup data source",
            )
        symbol_ids = payload.symbol_ids or result_uuid_list(run, "symbolIds")
        timeframes = payload.timeframes or default_timeframes(self.settings)
        generator = SyntheticFixtureGenerator(self.settings.synthetic_fixtures_default_seed)
        import_service = ImportService(self.session)
        import_batch_ids: list[str] = []
        for symbol_id in symbol_ids:
            symbol = await self.repository.get_symbol(symbol_id)
            if symbol is None:
                raise AppError(404, "symbol_not_found", "Symbol not found")
            for timeframe in timeframes:
                response = generator.generate(
                    SyntheticFixtureGenerateRequest(
                        pattern=SyntheticFixturePattern(payload.pattern),
                        symbol=symbol.symbol,
                        timeframe=timeframe,
                        start_time=datetime(2026, 1, 1, tzinfo=UTC),
                        candle_count=payload.candle_count,
                        volume_behavior=SyntheticVolumeBehavior.FLAT,
                        workspace_id=workspace_id,
                        user_id=run.user_id,
                        source_id=source_id,
                        symbol_id=symbol_id,
                    )
                )
                batch = await import_service.process_json_import(
                    JsonCandleImportRequest(
                        workspace_id=workspace_id,
                        user_id=run.user_id,
                        source_id=source_id,
                        symbol_id=symbol_id,
                        timeframe=timeframe,
                        candles=[
                            RawCandlePayload(**candle.model_dump(mode="python"))
                            for candle in response.candles
                        ],
                    )
                )
                import_batch_ids.append(str(batch.id))
        merge_result(run, {"demoImportBatchIds": import_batch_ids})
        return {
            "enabled": True,
            "importBatchIds": import_batch_ids,
            "productionDataMutated": False,
            "externalDataUsed": False,
        }

    async def run_readiness_check(
        self, run: WorkspaceSetupRun, payload: object
    ) -> dict[str, object]:
        assert isinstance(payload, ReadinessCheckStepInput)
        if not payload.run:
            return {"run": False}
        readiness = await ProductReadinessService(
            ProductReadinessRepository(self.session),
            settings=self.settings,
        ).run_readiness_check(run.workspace_id)
        result = {
            "readinessRunId": str(readiness.id),
            "readinessLabel": readiness.readiness_label.value,
            "readinessScore": readiness.readiness_score,
            "status": readiness.status.value,
            "blockerCount": len(readiness.blockers_json),
            "warningCount": len(readiness.warnings_json),
        }
        merge_result(run, {"readiness": result, "readinessRunId": result["readinessRunId"]})
        return result

    async def run_first_scan(self, run: WorkspaceSetupRun, payload: object) -> dict[str, object]:
        assert isinstance(payload, FirstScanStepInput)
        if not payload.run:
            return {"run": False}
        scan_config_id = payload.scan_config_id or uuid_or_none(run.result_json.get("scanConfigId"))
        if scan_config_id is None:
            raise AppError(422, "scan_config_required", "First scan requires a scan config")
        scan_config = await self.repository.get_scan_config(scan_config_id)
        if scan_config is None or scan_config.workspace_id != run.workspace_id:
            raise AppError(404, "scheduled_scan_config_not_found", "Scan config not found")
        scan_run = await MarketScanExecutor(self.session, self.settings).run_scan_config(
            scan_config_id,
            force=True,
        )
        merge_result(run, {"firstScanRunId": str(scan_run.id)})
        return {
            "run": True,
            "scanRunId": str(scan_run.id),
            "status": scan_run.status,
            "analysisRunCount": scan_run.analysis_run_count,
            "signalIds": scan_run.signal_ids_json,
        }

    async def load_run(self, setup_run_id: UUID) -> WorkspaceSetupRun:
        run = await self.repository.get_run(setup_run_id)
        if run is None:
            raise AppError(404, "workspace_setup_run_not_found", "Setup run not found")
        return run

    async def load_step_result(
        self,
        setup_run_id: UUID,
        step_key: WorkspaceSetupStepKey,
    ) -> WorkspaceSetupStepResult:
        step_result = await self.repository.get_step_result(setup_run_id, step_key.value)
        if step_result is None:
            raise AppError(404, "workspace_setup_step_not_found", "Setup step result not found")
        return step_result

    def update_run_progress(self, run: WorkspaceSetupRun) -> None:
        if run.status == WorkspaceSetupStatus.DRAFT.value:
            run.status = WorkspaceSetupStatus.RUNNING.value
        next_step = next_step_after(set(run.completed_steps_json) | set(run.skipped_steps_json))
        run.current_step = (next_step or WorkspaceSetupStepKey.FIRST_SCAN).value
        if not isinstance(run.result_json, dict):
            run.result_json = {}
        run.result_json = {**run.result_json, "safety": safety_payload()}


def parse_step_input(step_key: WorkspaceSetupStepKey, input_json: dict[str, object]) -> object:
    schema_by_step = {
        WorkspaceSetupStepKey.WORKSPACE: WorkspaceStepInput,
        WorkspaceSetupStepKey.USER: UserStepInput,
        WorkspaceSetupStepKey.SYMBOLS: SymbolsStepInput,
        WorkspaceSetupStepKey.DATA_SOURCE: DataSourceStepInput,
        WorkspaceSetupStepKey.CREDENTIAL_REFERENCE: CredentialReferenceStepInput,
        WorkspaceSetupStepKey.WATCHLIST: WatchlistStepInput,
        WorkspaceSetupStepKey.SCANNER_PRESET: ScannerPresetStepInput,
        WorkspaceSetupStepKey.PREFERENCE_PROFILE: PreferenceProfileStepInput,
        WorkspaceSetupStepKey.DEMO_DATA: DemoDataStepInput,
        WorkspaceSetupStepKey.READINESS_CHECK: ReadinessCheckStepInput,
        WorkspaceSetupStepKey.FIRST_SCAN: FirstScanStepInput,
    }
    try:
        return schema_by_step[step_key].model_validate(input_json)
    except ValidationError as error:
        message = "; ".join(str(item["msg"]) for item in error.errors())
        raise AppError(422, "workspace_setup_step_invalid", message) from error


def terminal_statuses() -> set[str]:
    return {
        WorkspaceSetupStatus.COMPLETED.value,
        WorkspaceSetupStatus.COMPLETED_WITH_WARNINGS.value,
        WorkspaceSetupStatus.FAILED.value,
        WorkspaceSetupStatus.CANCELLED.value,
    }


def require_run_workspace(run: WorkspaceSetupRun) -> UUID:
    if run.workspace_id is None:
        raise AppError(422, "workspace_setup_workspace_required", "Complete workspace setup first")
    return run.workspace_id


def mark_step_complete(run: WorkspaceSetupRun, step_key: WorkspaceSetupStepKey) -> None:
    run.completed_steps_json = sorted(set(run.completed_steps_json) | {step_key.value})
    run.failed_steps_json = [step for step in run.failed_steps_json if step != step_key.value]
    run.skipped_steps_json = [step for step in run.skipped_steps_json if step != step_key.value]


def mark_step_skipped(run: WorkspaceSetupRun, step_key: WorkspaceSetupStepKey) -> None:
    run.skipped_steps_json = sorted(set(run.skipped_steps_json) | {step_key.value})
    run.completed_steps_json = [step for step in run.completed_steps_json if step != step_key.value]
    run.failed_steps_json = [step for step in run.failed_steps_json if step != step_key.value]


def mark_step_failed(run: WorkspaceSetupRun, step_key: WorkspaceSetupStepKey) -> None:
    run.failed_steps_json = sorted(set(run.failed_steps_json) | {step_key.value})
    run.completed_steps_json = [step for step in run.completed_steps_json if step != step_key.value]


def merge_result(run: WorkspaceSetupRun, updates: dict[str, object]) -> None:
    current = run.result_json if isinstance(run.result_json, dict) else {}
    run.result_json = {**current, **updates}


def sanitize_input(
    step_key: WorkspaceSetupStepKey,
    input_json: dict[str, object],
) -> dict[str, object]:
    if step_key != WorkspaceSetupStepKey.CREDENTIAL_REFERENCE:
        return input_json
    sanitized = dict(input_json)
    if sanitized.get("secretRef"):
        sanitized["secretRef"] = "configured"
    if sanitized.get("secret_ref"):
        sanitized["secret_ref"] = "configured"
    return sanitized


def normalize_source_type(
    value: DataSourceType | str,
) -> DataSourceType:
    aliases = {
        "csv": DataSourceType.CSV_UPLOAD,
        "json": DataSourceType.JSON_IMPORT,
        "mock": DataSourceType.MANUAL_SEED,
        "provider": DataSourceType.API_POLLING,
        "live": DataSourceType.WEBSOCKET_LIVE,
    }
    if isinstance(value, DataSourceType):
        return value
    return aliases.get(value, DataSourceType(value))


def default_source_name(source_type: DataSourceType) -> str:
    return {
        DataSourceType.CSV_UPLOAD: "setup_csv_upload",
        DataSourceType.JSON_IMPORT: "setup_json_import",
        DataSourceType.API_POLLING: "setup_provider_polling",
        DataSourceType.WEBSOCKET_LIVE: "setup_live_feed",
        DataSourceType.MANUAL_SEED: "setup_manual_demo",
        DataSourceType.CHART_SCREENSHOT: "setup_chart_screenshot",
        DataSourceType.DERIVED_AGGREGATION: "setup_derived_aggregation",
    }[source_type]


def default_provider(source_type: DataSourceType) -> str:
    return {
        DataSourceType.CSV_UPLOAD: "csv",
        DataSourceType.JSON_IMPORT: "internal_json",
        DataSourceType.API_POLLING: "mock_polling",
        DataSourceType.WEBSOCKET_LIVE: "mock",
        DataSourceType.MANUAL_SEED: "manual",
        DataSourceType.CHART_SCREENSHOT: "manual_ocr",
        DataSourceType.DERIVED_AGGREGATION: "internal",
    }[source_type]


def default_timeframes(settings: Settings) -> list[Timeframe]:
    values = [
        item.strip()
        for item in settings.workspace_setup_default_timeframes.split(",")
        if item.strip()
    ]
    return [Timeframe(value) for value in values] or [Timeframe.ONE_MINUTE]


def result_uuid_list(run: WorkspaceSetupRun, key: str) -> list[UUID]:
    values = run.result_json.get(key) if isinstance(run.result_json, dict) else []
    if not isinstance(values, list):
        return []
    return [UUID(str(value)) for value in values]


def uuid_or_none(value: object) -> UUID | None:
    if value is None or value == "":
        return None
    return UUID(str(value))


def source_is_demo_safe(source_type: str, provider: str, config_json: dict[str, object]) -> bool:
    if bool(config_json.get("demo")) or bool(config_json.get("syntheticFixtures")):
        return True
    return source_type == DataSourceType.MANUAL_SEED.value or provider in {
        "mock",
        "manual",
        "internal_json",
        "mock_polling",
    }


def build_symbol_create(symbol_code: str, market_type: MarketType) -> SymbolCreate:
    if market_type == MarketType.CRYPTO:
        return SymbolCreate(
            symbol=symbol_code,
            display_name=symbol_code,
            market_type=market_type,
            base_asset=symbol_code.removesuffix("USDT") or symbol_code,
            quote_asset="USDT" if symbol_code.endswith("USDT") else None,
            tick_size=Decimal("0.01"),
        )
    if market_type == MarketType.FOREX:
        return SymbolCreate(
            symbol=symbol_code,
            display_name=symbol_code,
            market_type=market_type,
            base_asset=symbol_code[:3] if len(symbol_code) >= 6 else None,
            quote_asset=symbol_code[3:6] if len(symbol_code) >= 6 else None,
            pip_size=Decimal("0.0001"),
        )
    return SymbolCreate(
        symbol=symbol_code,
        display_name=symbol_code,
        market_type=market_type,
        base_asset=symbol_code,
        tick_size=Decimal("0.01"),
    )


def safety_payload() -> dict[str, object]:
    return {
        "brokerExecution": False,
        "orders": False,
        "autoTrading": False,
        "tradingAlerts": False,
        "financialAdvice": False,
        "hiddenScans": False,
    }
