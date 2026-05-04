from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.preference_profiles.matcher import (
    PreferenceProfileMatcher,
    PreferenceSignalContext,
)
from app.modules.preference_profiles.models import (
    PersonalStrategyPreferenceProfile,
    PreferenceProfileStatus,
)
from app.modules.preference_profiles.repository import PreferenceProfileRepository
from app.modules.preference_profiles.schemas import (
    PreferenceProfileCreate,
    PreferenceProfileFilterContextRead,
    PreferenceProfileMatchRead,
    PreferenceProfileRead,
    PreferenceProfileUpdate,
)
from app.modules.signals.models import Signal


class PreferenceProfileService:
    def __init__(
        self,
        session: AsyncSession,
        repository: PreferenceProfileRepository | None = None,
        matcher: PreferenceProfileMatcher | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or PreferenceProfileRepository(session)
        self.matcher = matcher or PreferenceProfileMatcher()
        self.settings = settings or get_settings()

    async def create_preference_profile(
        self,
        payload: PreferenceProfileCreate,
    ) -> PersonalStrategyPreferenceProfile:
        await self.validate_workspace(payload.workspace_id)
        await self.validate_user(payload.workspace_id, payload.user_id)
        await self.validate_symbol_ids(payload.symbol_ids_json + payload.excluded_symbol_ids_json)
        profile = PersonalStrategyPreferenceProfile(
            workspace_id=payload.workspace_id,
            user_id=payload.user_id,
            name=payload.name,
            description=payload.description,
            status=PreferenceProfileStatus.ACTIVE.value,
            is_default=payload.is_default,
            market_types_json=[item.value for item in payload.market_types_json],
            symbol_ids_json=[str(item) for item in payload.symbol_ids_json],
            excluded_symbol_ids_json=[str(item) for item in payload.excluded_symbol_ids_json],
            timeframes_json=[item.value for item in payload.timeframes_json],
            session_labels_json=[item.value for item in payload.session_labels_json],
            pattern_types_json=payload.pattern_types_json,
            excluded_pattern_types_json=payload.excluded_pattern_types_json,
            strategy_profile_keys_json=payload.strategy_profile_keys_json,
            minimum_confidence=payload.minimum_confidence,
            minimum_setup_quality=payload.minimum_setup_quality,
            max_stale_seconds=self.resolve_max_stale_seconds(
                payload.max_stale_seconds,
                payload.require_fresh_data,
            ),
            require_fresh_data=payload.require_fresh_data,
            require_timeframe_agreement=payload.require_timeframe_agreement,
            require_acceptable_data_quality=payload.require_acceptable_data_quality,
            include_news_context=payload.include_news_context,
            include_outcomes=payload.include_outcomes,
            notification_preferences_json=payload.notification_preferences_json,
            metadata_json=payload.metadata_json,
        )
        try:
            created = await self.repository.create(profile)
            if created.is_default:
                await self.repository.clear_default_profiles(created.workspace_id, created.id)
            await self.session.commit()
            await self.session.refresh(created)
            return created
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "preference_profile_conflict",
                "Preference profile could not be created",
            ) from error

    async def list_preference_profiles(
        self,
        workspace_id: UUID,
        user_id: UUID | None,
        status: PreferenceProfileStatus | None,
        include_archived: bool,
        limit: int,
        offset: int,
    ) -> list[PersonalStrategyPreferenceProfile]:
        await self.validate_workspace(workspace_id)
        await self.validate_user(workspace_id, user_id)
        return await self.repository.list_profiles(
            workspace_id=workspace_id,
            user_id=user_id,
            status=status.value if status is not None else None,
            include_archived=include_archived,
            limit=limit,
            offset=offset,
        )

    async def get_preference_profile(
        self,
        profile_id: UUID,
    ) -> PersonalStrategyPreferenceProfile:
        profile = await self.repository.get_by_id(profile_id)
        if profile is None:
            raise AppError(404, "preference_profile_not_found", "Preference profile not found")
        return profile

    async def get_default_preference_profile(
        self,
        workspace_id: UUID,
        user_id: UUID | None = None,
    ) -> PersonalStrategyPreferenceProfile:
        await self.validate_workspace(workspace_id)
        await self.validate_user(workspace_id, user_id)
        profile = await self.repository.get_default_profile(workspace_id, user_id)
        if profile is None:
            raise AppError(
                404,
                "preference_profile_not_found",
                "Default preference profile not found",
            )
        return profile

    async def update_preference_profile(
        self,
        profile_id: UUID,
        payload: PreferenceProfileUpdate,
    ) -> PersonalStrategyPreferenceProfile:
        profile = await self.get_preference_profile(profile_id)
        updates = payload.model_dump(exclude_unset=True, mode="python")
        user_id = updates.get("user_id", profile.user_id)
        await self.validate_user(profile.workspace_id, user_id)
        symbol_ids = updates.get("symbol_ids_json", profile.symbol_ids_json)
        excluded_symbol_ids = updates.get(
            "excluded_symbol_ids_json",
            profile.excluded_symbol_ids_json,
        )
        await self.validate_symbol_ids([*symbol_ids, *excluded_symbol_ids])
        if (
            updates.get("require_fresh_data") is True
            and "max_stale_seconds" not in updates
            and profile.max_stale_seconds is None
        ):
            updates["max_stale_seconds"] = (
                self.settings.preference_profile_default_max_stale_seconds
            )
        for field_name, field_value in updates.items():
            setattr(profile, field_name, convert_profile_update_value(field_name, field_value))
        try:
            updated = await self.repository.update(profile)
            if updated.is_default:
                await self.repository.clear_default_profiles(updated.workspace_id, updated.id)
            await self.session.commit()
            await self.session.refresh(updated)
            return updated
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "preference_profile_conflict",
                "Preference profile could not be updated",
            ) from error

    async def archive_preference_profile(
        self,
        profile_id: UUID,
    ) -> PersonalStrategyPreferenceProfile:
        profile = await self.get_preference_profile(profile_id)
        profile.status = PreferenceProfileStatus.ARCHIVED.value
        profile.is_default = False
        updated = await self.repository.update(profile)
        await self.session.commit()
        await self.session.refresh(updated)
        return updated

    async def set_default_profile(self, profile_id: UUID) -> PersonalStrategyPreferenceProfile:
        profile = await self.get_preference_profile(profile_id)
        if profile.status != PreferenceProfileStatus.ACTIVE.value:
            raise AppError(
                422,
                "preference_profile_not_active",
                "Only active preference profiles can be set as default",
            )
        profile.is_default = True
        updated = await self.repository.update(profile)
        await self.repository.clear_default_profiles(updated.workspace_id, updated.id)
        await self.session.commit()
        await self.session.refresh(updated)
        return updated

    async def match_signal(self, profile_id: UUID, signal_id: UUID) -> PreferenceProfileMatchRead:
        profile = await self.get_preference_profile(profile_id)
        context = await self.load_signal_context(signal_id)
        if context.signal.workspace_id != profile.workspace_id:
            raise AppError(
                404,
                "signal_not_found",
                "Signal not found for preference profile workspace",
            )
        result = self.matcher.match(profile, context)
        return PreferenceProfileMatchRead(
            profile_id=profile.id,
            signal_id=context.signal.id,
            matches=result.matches,
            included_reasons=result.included_reasons,
            excluded_reasons=result.excluded_reasons,
            preference_warnings=result.preference_warnings,
        )

    async def filter_signal_summaries(
        self,
        profile_id: UUID,
        signals: list[Signal],
    ) -> list[Signal]:
        profile = await self.get_preference_profile(profile_id)
        filtered: list[Signal] = []
        for signal in signals:
            if signal.workspace_id != profile.workspace_id:
                continue
            context = await self.load_signal_context(signal.id)
            result = self.matcher.match(profile, context)
            if result.matches:
                filtered.append(signal)
        return filtered

    async def build_filter_context(self, profile_id: UUID) -> PreferenceProfileFilterContextRead:
        profile = await self.get_preference_profile(profile_id)
        return PreferenceProfileFilterContextRead(
            profile=PreferenceProfileRead.model_validate(profile),
            filters={
                "marketTypes": profile.market_types_json,
                "symbolIds": profile.symbol_ids_json,
                "excludedSymbolIds": profile.excluded_symbol_ids_json,
                "timeframes": profile.timeframes_json,
                "sessionLabels": profile.session_labels_json,
                "patternTypes": profile.pattern_types_json,
                "excludedPatternTypes": profile.excluded_pattern_types_json,
                "strategyProfileKeys": profile.strategy_profile_keys_json,
                "minimumConfidence": (
                    str(profile.minimum_confidence)
                    if profile.minimum_confidence is not None
                    else None
                ),
                "minimumSetupQuality": (
                    str(profile.minimum_setup_quality)
                    if profile.minimum_setup_quality is not None
                    else None
                ),
                "maxStaleSeconds": profile.max_stale_seconds,
                "requireFreshData": profile.require_fresh_data,
                "requireTimeframeAgreement": profile.require_timeframe_agreement,
                "requireAcceptableDataQuality": profile.require_acceptable_data_quality,
                "includeNewsContext": profile.include_news_context,
                "includeOutcomes": profile.include_outcomes,
                "notificationPreferences": profile.notification_preferences_json,
            },
            safety_boundaries=[
                "Preferences filter review workflows only.",
                "Preferences do not mutate deterministic strategy profiles.",
                "Preferences do not change signal classification.",
                "Preferences do not execute broker or order workflows.",
                "Preferences do not provide financial advice.",
            ],
        )

    async def load_signal_context(self, signal_id: UUID) -> PreferenceSignalContext:
        signal = await self.repository.get_signal(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        symbol = await self.repository.get_symbol(signal.symbol_id)
        return PreferenceSignalContext(
            signal=signal,
            symbol=symbol,
            setup_context=await self.repository.get_latest_setup_context(signal.id),
            market_session=await self.repository.get_latest_market_session(signal),
            market_memory=await self.repository.get_latest_market_memory(signal),
        )

    async def validate_workspace(self, workspace_id: UUID) -> None:
        workspace = await self.repository.get_workspace(workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")

    async def validate_user(self, workspace_id: UUID, user_id: UUID | None) -> None:
        if user_id is None:
            return
        user = await self.repository.get_user(user_id)
        if user is None or user.workspace_id != workspace_id:
            raise AppError(404, "user_not_found", "User not found for workspace")

    async def validate_symbol_ids(self, symbol_ids: list[UUID | str]) -> None:
        for symbol_id in symbol_ids:
            symbol = await self.repository.get_symbol(UUID(str(symbol_id)))
            if symbol is None:
                raise AppError(404, "symbol_not_found", "Symbol not found")

    def resolve_max_stale_seconds(
        self,
        max_stale_seconds: int | None,
        require_fresh_data: bool,
    ) -> int | None:
        if max_stale_seconds is not None:
            return max_stale_seconds
        if require_fresh_data:
            return self.settings.preference_profile_default_max_stale_seconds
        return None


def convert_profile_update_value(field_name: str, value: object) -> object:
    if field_name == "status" and isinstance(value, PreferenceProfileStatus):
        return value.value
    if field_name == "market_types_json":
        return [item.value if hasattr(item, "value") else str(item) for item in value]
    if field_name in {"timeframes_json", "session_labels_json"}:
        return [item.value if hasattr(item, "value") else str(item) for item in value]
    if field_name in {"symbol_ids_json", "excluded_symbol_ids_json"}:
        return [str(item) for item in value]
    return value
