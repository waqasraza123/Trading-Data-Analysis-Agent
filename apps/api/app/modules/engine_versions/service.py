from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.engine_versions.models import EngineVersion
from app.modules.engine_versions.registry import (
    CURRENT_ENGINE_VERSIONS,
    current_engine_snapshot,
    is_supported_engine_snapshot,
)
from app.modules.engine_versions.repository import EngineVersionRepository


class EngineVersionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = EngineVersionRepository(session)

    async def list_versions(self) -> list[EngineVersion]:
        return await self.repository.list_versions()

    async def list_by_engine_name(self, engine_name: str) -> list[EngineVersion]:
        versions = await self.repository.list_by_engine_name(engine_name)
        if not versions:
            raise AppError(404, "engine_version_not_found", "Engine version not found")
        return versions

    async def seed_current_versions(self) -> list[EngineVersion]:
        seeded_versions: list[EngineVersion] = []
        for definition in CURRENT_ENGINE_VERSIONS:
            existing_version = await self.repository.get_by_engine_version(
                definition.engine_name,
                definition.version,
            )
            if existing_version is None:
                existing_version = await self.repository.create(
                    EngineVersion(
                        engine_name=definition.engine_name,
                        version=definition.version,
                        description=definition.description,
                        config_json=definition.config_json,
                    )
                )
            else:
                existing_version.description = definition.description
                existing_version.config_json = definition.config_json
            seeded_versions.append(existing_version)
        await self.session.flush()
        return seeded_versions

    def current_snapshot(self) -> dict[str, object]:
        return current_engine_snapshot()

    def validate_supported_snapshot(self, snapshot: dict[str, object] | None) -> None:
        if not is_supported_engine_snapshot(snapshot):
            raise AppError(
                422,
                "unsupported_engine_version",
                "Replay references an engine version that is not registered in this codebase",
            )
