import argparse
import asyncio
import json

from app.config import get_settings
from app.db.session import get_async_session_factory
from app.modules.seeding.service import SeedService


async def run_seed_command() -> None:
    session_factory = get_async_session_factory()
    if session_factory is None:
        msg = "DATABASE_URL is not configured"
        raise RuntimeError(msg)
    async with session_factory() as session:
        result = await SeedService(session).seed(get_settings())
        print(json.dumps(result.__dict__, default=str, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("seed")
    args = parser.parse_args()
    if args.command == "seed":
        asyncio.run(run_seed_command())


if __name__ == "__main__":
    main()
