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
from app.modules.demo_mode.schemas import DemoModeRunRequest
from app.modules.demo_mode.service import DemoModeService
from app.modules.seeding.service import SeedService
from app.modules.smoke.service import SmokeService
from app.modules.synthetic_fixtures.generator import SyntheticFixtureGenerator
from app.modules.synthetic_fixtures.schemas import (
    SyntheticFixtureGenerateRequest,
    SyntheticFixtureOutputFormat,
    SyntheticFixturePattern,
    SyntheticVolumeBehavior,
)


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
                "scanner_preset_count": result.scanner_preset_count,
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


async def run_demo_full_flow_command(database_url_env: str) -> None:
    configure_database_url(database_url_env, allow_test_fallback=True)
    settings = get_settings()
    configure_logging(settings.log_level)
    session_factory = get_async_session_factory()
    if session_factory is None:
        msg = "DATABASE_URL is not configured"
        raise RuntimeError(msg)
    async with session_factory() as session:
        result = await DemoModeService(session, settings).run_full_demo_flow(DemoModeRunRequest())
        print(
            json.dumps(
                result.model_dump(mode="json", by_alias=True),
                default=str,
                sort_keys=True,
            )
        )


def run_synthetic_fixture_generate_command(args: argparse.Namespace) -> None:
    settings = get_settings()
    request = SyntheticFixtureGenerateRequest(
        pattern=args.pattern,
        symbol=args.symbol,
        timeframe=args.timeframe,
        start_time=args.start_time,
        candle_count=args.candle_count,
        start_price=args.start_price,
        volatility=args.volatility,
        volume_behavior=args.volume_behavior,
        seed=args.seed,
        include_malformed=args.include_malformed,
        output_format=args.output_format,
        workspace_id=args.workspace_id,
        user_id=args.user_id,
        source_id=args.source_id,
        symbol_id=args.symbol_id,
    )
    response = SyntheticFixtureGenerator(settings.synthetic_fixtures_default_seed).generate(request)
    if request.output_format == SyntheticFixtureOutputFormat.CSV:
        print(response.csv_text or "")
        return
    if request.output_format == SyntheticFixtureOutputFormat.JSON_IMPORT_PAYLOAD:
        print(json.dumps(response.json_import_payload, default=str, sort_keys=True))
        return
    if request.output_format == SyntheticFixtureOutputFormat.CANDLES:
        candles = [candle.model_dump(mode="json") for candle in response.candles]
        print(json.dumps(candles, default=str, sort_keys=True))
        return
    print(
        json.dumps(
            response.model_dump(mode="json", by_alias=True, exclude_none=True),
            default=str,
            sort_keys=True,
        )
    )


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
    synthetic_parser = subparsers.add_parser("synthetic-fixtures")
    synthetic_subparsers = synthetic_parser.add_subparsers(
        dest="synthetic_command",
        required=True,
    )
    generate_parser = synthetic_subparsers.add_parser("generate")
    generate_parser.add_argument(
        "--pattern",
        choices=[pattern.value for pattern in SyntheticFixturePattern],
        required=True,
    )
    generate_parser.add_argument("--symbol", default="EURUSD")
    generate_parser.add_argument("--timeframe", default="1m")
    generate_parser.add_argument("--start-time", default="2026-01-01T00:00:00Z")
    generate_parser.add_argument("--candle-count", type=int, default=40)
    generate_parser.add_argument("--start-price", default="1.1000")
    generate_parser.add_argument("--volatility", default="0.0005")
    generate_parser.add_argument(
        "--volume-behavior",
        choices=[behavior.value for behavior in SyntheticVolumeBehavior],
        default=SyntheticVolumeBehavior.FLAT.value,
    )
    generate_parser.add_argument("--seed", type=int, default=None)
    generate_parser.add_argument("--include-malformed", action="store_true")
    generate_parser.add_argument(
        "--output-format",
        choices=[output_format.value for output_format in SyntheticFixtureOutputFormat],
        default=SyntheticFixtureOutputFormat.CANDLES.value,
    )
    generate_parser.add_argument("--workspace-id", default=None)
    generate_parser.add_argument("--user-id", default=None)
    generate_parser.add_argument("--source-id", default=None)
    generate_parser.add_argument("--symbol-id", default=None)
    demo_parser = subparsers.add_parser("demo")
    demo_subparsers = demo_parser.add_subparsers(dest="demo_command", required=True)
    demo_run_parser = demo_subparsers.add_parser("run-full-flow")
    demo_run_parser.add_argument("--database-url-env", default="DATABASE_URL")
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
    if args.command == "synthetic-fixtures" and args.synthetic_command == "generate":
        run_synthetic_fixture_generate_command(args)
    if args.command == "demo" and args.demo_command == "run-full-flow":
        asyncio.run(run_demo_full_flow_command(database_url_env=args.database_url_env))


if __name__ == "__main__":
    main()
