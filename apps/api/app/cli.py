import argparse
import asyncio
import json
import logging
import os
from pathlib import Path

from app.config import get_settings
from app.core.database_safety import validate_smoke_database_target
from app.core.logging import configure_logging
from app.db.session import get_async_session_factory
from app.modules.seeding.service import SeedService
from app.modules.smoke.service import SmokeService


async def run_seed_command() -> None:
    configure_database_url("DATABASE_URL", allow_test_fallback=True)
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(settings.service_name)
    session_factory = get_async_session_factory()
    if session_factory is None:
        msg = "DATABASE_URL is not configured"
        raise RuntimeError(msg)
    logger.info("seed_started")
    async with session_factory() as session:
        result = await SeedService(session).seed(settings)
        logger.info(
            "seed_completed",
            extra={
                "symbol_count": result.symbol_count,
                "data_source_count": result.data_source_count,
                "strategy_profile_count": result.strategy_profile_count,
                "engine_version_count": result.engine_version_count,
            },
        )
        print(json.dumps(result.__dict__, default=str, sort_keys=True))


async def run_smoke_command(database_url_env: str, include_write_tests: bool) -> None:
    configured_database_url = os.environ.get("DATABASE_URL")
    database_url = configure_database_url(database_url_env, allow_test_fallback=False)
    validate_smoke_database_target(
        database_url_env=database_url_env,
        target_database_url=database_url,
        database_url=configured_database_url,
        app_env=os.environ.get("APP_ENV"),
        env=os.environ.get("ENV"),
        include_write_tests=include_write_tests,
    )
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(settings.service_name)
    session_factory = get_async_session_factory()
    if session_factory is None:
        msg = "DATABASE_URL is not configured"
        raise RuntimeError(msg)
    logger.info(
        "smoke_started",
        extra={"database_url_env": database_url_env, "write_tests": include_write_tests},
    )
    api_root = Path(__file__).resolve().parents[1]
    async with session_factory() as session:
        result = await SmokeService(session, api_root).run(
            settings=settings,
            database_url_env=database_url_env,
            include_write_tests=include_write_tests,
        )
        logger.info(
            "smoke_completed",
            extra={
                "database_url_env": database_url_env,
                "write_tests": include_write_tests,
            },
        )
        print(json.dumps(result.to_dict(), default=str, sort_keys=True))


def configure_database_url(database_url_env: str, allow_test_fallback: bool) -> str:
    database_url = os.environ.get(database_url_env)
    if database_url is None and allow_test_fallback:
        database_url = os.environ.get("TEST_DATABASE_URL")
        database_url_env = "TEST_DATABASE_URL"
    if database_url is None:
        msg = f"{database_url_env} is not configured"
        raise RuntimeError(msg)
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    return database_url


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("seed")
    smoke_parser = subparsers.add_parser("smoke")
    smoke_parser.add_argument("--database-url-env", default="TEST_DATABASE_URL")
    write_group = smoke_parser.add_mutually_exclusive_group()
    write_group.add_argument("--skip-write-tests", action="store_true", default=True)
    write_group.add_argument("--include-write-tests", action="store_true")
    args = parser.parse_args()
    if args.command == "seed":
        asyncio.run(run_seed_command())
    if args.command == "smoke":
        asyncio.run(
            run_smoke_command(
                database_url_env=args.database_url_env,
                include_write_tests=args.include_write_tests,
            )
        )


if __name__ == "__main__":
    main()
