from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.analysis.models import AnalysisReplayMode, AnalysisRunStatus
from app.modules.analysis.schemas import AnalysisReplayRequest, AnalysisRunCreate
from app.modules.analysis.service import AnalysisService
from app.modules.candles.normalizer import RawCandlePayload
from app.modules.candles.timeframes import Timeframe
from app.modules.engine_versions.service import EngineVersionService
from app.modules.imports.schemas import JsonCandleImportRequest
from app.modules.imports.service import ImportService
from app.modules.seeding.service import SeedService
from app.modules.signals.service import SignalClassificationService
from app.modules.strategy_profiles.service import StrategyProfileService
from app.modules.symbols.repository import SymbolRepository

CRITICAL_TABLES = {
    "workspaces",
    "users",
    "symbols",
    "data_sources",
    "import_batches",
    "candles",
    "live_feed_subscriptions",
    "live_feed_events",
    "analysis_runs",
    "feature_snapshots",
    "indicator_snapshots",
    "pattern_candidates",
    "strategy_profiles",
    "signals",
    "signal_confidence_components",
    "signal_evidence",
    "signal_risk_notes",
    "deterministic_explanations",
    "engine_versions",
}


@dataclass(frozen=True)
class SmokeCheck:
    name: str
    status: str
    details: dict[str, object]


@dataclass(frozen=True)
class SmokeResult:
    database_url_env: str
    write_tests: bool
    checks: list[SmokeCheck]

    def to_dict(self) -> dict[str, object]:
        return {
            "databaseUrlEnv": self.database_url_env,
            "writeTests": self.write_tests,
            "checks": [
                {"name": check.name, "status": check.status, "details": check.details}
                for check in self.checks
            ],
        }


class SmokeService:
    def __init__(self, session: AsyncSession, api_root: Path) -> None:
        self.session = session
        self.api_root = api_root

    async def run(
        self,
        settings: Settings,
        database_url_env: str,
        include_write_tests: bool,
    ) -> SmokeResult:
        checks = [
            await self.check_connectivity(),
            self.check_single_alembic_head(),
            await self.check_database_revision(),
            await self.check_critical_tables(),
            await self.check_engine_versions_query(),
            await self.check_strategy_profiles_query(),
        ]
        if include_write_tests:
            checks.extend(await self.run_write_checks(settings))
        return SmokeResult(
            database_url_env=database_url_env,
            write_tests=include_write_tests,
            checks=checks,
        )

    async def check_connectivity(self) -> SmokeCheck:
        result = await self.session.execute(text("select 1"))
        return SmokeCheck("db_connectivity", "passed", {"value": int(result.scalar_one())})

    def check_single_alembic_head(self) -> SmokeCheck:
        alembic_config = Config(str(self.api_root / "alembic.ini"))
        alembic_config.set_main_option("script_location", str(self.api_root / "alembic"))
        script = ScriptDirectory.from_config(alembic_config)
        heads = list(script.get_heads())
        return SmokeCheck(
            "alembic_single_head",
            "passed" if len(heads) == 1 else "failed",
            {"heads": heads},
        )

    async def check_database_revision(self) -> SmokeCheck:
        result = await self.session.execute(text("select version_num from alembic_version"))
        database_revision = str(result.scalar_one())
        head_revision = self.current_head_revision()
        return SmokeCheck(
            "alembic_database_head",
            "passed" if database_revision == head_revision else "failed",
            {"databaseRevision": database_revision, "headRevision": head_revision},
        )

    async def check_critical_tables(self) -> SmokeCheck:
        result = await self.session.execute(
            text(
                "select table_name from information_schema.tables "
                "where table_schema = 'public' and table_type = 'BASE TABLE'"
            )
        )
        existing_tables = {str(row[0]) for row in result.all()}
        missing_tables = sorted(CRITICAL_TABLES.difference(existing_tables))
        return SmokeCheck(
            "critical_tables",
            "passed" if not missing_tables else "failed",
            {"missingTables": missing_tables},
        )

    async def check_engine_versions_query(self) -> SmokeCheck:
        versions = await EngineVersionService(self.session).list_versions()
        return SmokeCheck("engine_versions_query", "passed", {"count": len(versions)})

    async def check_strategy_profiles_query(self) -> SmokeCheck:
        profiles = await StrategyProfileService(self.session).list_profiles(limit=100, offset=0)
        return SmokeCheck("strategy_profiles_query", "passed", {"count": len(profiles)})

    async def run_write_checks(self, settings: Settings) -> list[SmokeCheck]:
        seed_settings = settings.model_copy(
            update={
                "seed_default_workspace_name": "Smoke Workspace",
                "seed_default_admin_email": "smoke-admin@example.test",
                "seed_default_admin_name": "Smoke Admin",
            }
        )
        first_seed = await SeedService(self.session).seed(seed_settings)
        second_seed = await SeedService(self.session).seed(seed_settings)
        analysis_check = await self.run_import_analyze_replay_check(second_seed.workspace_id)
        return [
            SmokeCheck(
                "seed_idempotency",
                "passed",
                {
                    "workspaceIdStable": first_seed.workspace_id == second_seed.workspace_id,
                    "adminUserIdStable": first_seed.admin_user_id == second_seed.admin_user_id,
                    "symbolCount": second_seed.symbol_count,
                    "dataSourceCount": second_seed.data_source_count,
                    "strategyProfileCount": second_seed.strategy_profile_count,
                    "engineVersionCount": second_seed.engine_version_count,
                    "scannerPresetCount": second_seed.scanner_preset_count,
                },
            ),
            analysis_check,
        ]

    async def run_import_analyze_replay_check(self, workspace_id: UUID | None) -> SmokeCheck:
        if workspace_id is None:
            return SmokeCheck(
                "import_analyze_replay",
                "failed",
                {"reason": "seed did not create a workspace"},
            )
        symbol = await SymbolRepository(self.session).get_by_symbol("EURUSD")
        source_result = await self.session.execute(
            text(
                "select id from data_sources where workspace_id = :workspace_id "
                "and name = 'json_import' limit 1"
            ),
            {"workspace_id": workspace_id},
        )
        user_result = await self.session.execute(
            text(
                "select id from users where workspace_id = :workspace_id "
                "and email = 'smoke-admin@example.test' limit 1"
            ),
            {"workspace_id": workspace_id},
        )
        source_id = source_result.scalar_one_or_none()
        user_id = user_result.scalar_one_or_none()
        if symbol is None or source_id is None or user_id is None:
            return SmokeCheck(
                "import_analyze_replay",
                "failed",
                {
                    "symbolFound": symbol is not None,
                    "sourceFound": source_id is not None,
                    "userFound": user_id is not None,
                },
            )
        candles = smoke_candles()
        await ImportService(self.session).process_json_import(
            JsonCandleImportRequest(
                workspace_id=workspace_id,
                user_id=user_id,
                source_id=source_id,
                symbol_id=symbol.id,
                timeframe=Timeframe.ONE_MINUTE,
                candles=candles,
            )
        )
        analysis_run = await AnalysisService(self.session).create_historical_run(
            AnalysisRunCreate(
                workspace_id=workspace_id,
                user_id=user_id,
                source_id=source_id,
                symbol_id=symbol.id,
                timeframe=Timeframe.ONE_MINUTE,
                start_time=candles[12].timestamp,
                end_time=candles[-1].timestamp,
                warmup_start_time=candles[0].timestamp,
                baseline_start_time=candles[0].timestamp,
            )
        )
        replay_run = await AnalysisService(self.session).replay_run(
            analysis_run.id,
            AnalysisReplayRequest(mode=AnalysisReplayMode.LATEST_ENGINE_VERSION),
        )
        signal_response = await SignalClassificationService(self.session).get_by_analysis_run_id(
            replay_run.id
        )
        return SmokeCheck(
            "import_analyze_replay",
            "passed" if replay_run.status == AnalysisRunStatus.COMPLETED else "failed",
            {
                "analysisRunId": str(analysis_run.id),
                "analysisStatus": analysis_run.status,
                "replayRunId": str(replay_run.id),
                "replayStatus": replay_run.status,
                "signalId": str(signal_response.signal.id),
                "explanationPresent": signal_response.deterministic_explanation is not None,
            },
        )

    def current_head_revision(self) -> str:
        alembic_config = Config(str(self.api_root / "alembic.ini"))
        alembic_config.set_main_option("script_location", str(self.api_root / "alembic"))
        script = ScriptDirectory.from_config(alembic_config)
        return str(script.get_current_head())


def smoke_candles() -> list[RawCandlePayload]:
    start_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC) + timedelta(
        minutes=uuid4().int % 1000000
    )
    candles: list[RawCandlePayload] = []
    for index in range(24):
        base = Decimal("1.1000") + Decimal(index) * Decimal("0.0005")
        candles.append(
            RawCandlePayload(
                timestamp=start_time + timedelta(minutes=index),
                open=str(base),
                high=str(base + Decimal("0.0008")),
                low=str(base - Decimal("0.0002")),
                close=str(base + Decimal("0.0006")),
                volume=str(Decimal("100") + Decimal(index)),
            )
        )
    return candles
