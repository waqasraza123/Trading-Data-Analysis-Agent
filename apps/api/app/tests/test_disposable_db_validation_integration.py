from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


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


def test_alembic_has_single_head() -> None:
    api_root = Path(__file__).resolve().parents[2]
    alembic_config = Config(str(api_root / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(api_root / "alembic"))
    script = ScriptDirectory.from_config(alembic_config)

    assert script.get_heads() == ["f9eb9423c4a2"]


@pytest.mark.asyncio
async def test_migrated_test_database_is_at_head_and_has_critical_tables(
    db_session: AsyncSession,
) -> None:
    version_result = await db_session.execute(text("select version_num from alembic_version"))
    assert version_result.scalar_one() == "f9eb9423c4a2"

    table_result = await db_session.execute(
        text(
            "select table_name from information_schema.tables "
            "where table_schema = 'public' and table_type = 'BASE TABLE'"
        )
    )
    existing_tables = {str(row[0]) for row in table_result.all()}

    assert CRITICAL_TABLES.issubset(existing_tables)
