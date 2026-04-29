from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.strategy_profiles.models import StrategyProfile
from app.modules.strategy_profiles.repository import StrategyProfileRepository
from app.modules.strategy_profiles.seeds import DEFAULT_STRATEGY_PROFILES


class StrategyProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = StrategyProfileRepository(session)

    async def list_profiles(
        self,
        limit: int,
        offset: int,
        is_active: bool | None = None,
    ) -> list[StrategyProfile]:
        return await self.repository.list_profiles(limit=limit, offset=offset, is_active=is_active)

    async def get_by_key(self, key: str) -> StrategyProfile:
        profile = await self.repository.get_by_key(key)
        if profile is None:
            raise AppError(404, "strategy_profile_not_found", "Strategy profile not found")
        return profile

    async def seed_default_profiles(self) -> list[StrategyProfile]:
        profiles: list[StrategyProfile] = []
        for definition in DEFAULT_STRATEGY_PROFILES:
            existing_profile = await self.repository.get_by_key_version(
                definition.key,
                definition.version,
            )
            if existing_profile is not None:
                profiles.append(existing_profile)
                continue
            profiles.append(
                await self.repository.create(
                    StrategyProfile(
                        key=definition.key,
                        name=definition.name,
                        description=definition.description,
                        version=definition.version,
                        is_active=True,
                        allowed_patterns_json=list(definition.allowed_patterns),
                        excluded_patterns_json=list(definition.excluded_patterns),
                        minimum_candidate_strength=definition.minimum_candidate_strength,
                        minimum_confidence=definition.minimum_confidence,
                        component_weights_json=definition.component_weights,
                        risk_filters_json=definition.risk_filters,
                        no_signal_rules_json=definition.no_signal_rules,
                    )
                )
            )
        await self.session.flush()
        return profiles
