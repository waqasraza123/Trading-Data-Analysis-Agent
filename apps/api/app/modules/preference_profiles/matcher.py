from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.core.time import utc_now
from app.modules.market_memory.models import RollingMarketStateSnapshot
from app.modules.market_sessions.models import MarketSessionContext
from app.modules.preference_profiles.models import PersonalStrategyPreferenceProfile
from app.modules.setup_context.models import SetupContext
from app.modules.signals.models import Signal
from app.modules.symbols.models import Symbol


@dataclass(frozen=True)
class PreferenceSignalContext:
    signal: Signal
    symbol: Symbol | None = None
    setup_context: SetupContext | None = None
    market_session: MarketSessionContext | None = None
    market_memory: RollingMarketStateSnapshot | None = None
    evaluated_at: datetime | None = None


@dataclass(frozen=True)
class PreferenceMatchResult:
    matches: bool
    included_reasons: list[str]
    excluded_reasons: list[str]
    preference_warnings: list[str]


class PreferenceProfileMatcher:
    def match(
        self,
        profile: PersonalStrategyPreferenceProfile,
        context: PreferenceSignalContext,
    ) -> PreferenceMatchResult:
        included_reasons: list[str] = []
        excluded_reasons: list[str] = []
        preference_warnings: list[str] = []
        signal = context.signal
        symbol_id = str(signal.symbol_id)

        if profile.status != "active":
            excluded_reasons.append(f"Preference profile is {profile.status}.")

        if profile.symbol_ids_json:
            if symbol_id in profile.symbol_ids_json:
                included_reasons.append("Signal symbol is in the preferred symbol list.")
            else:
                excluded_reasons.append("Signal symbol is outside the preferred symbol list.")

        if symbol_id in profile.excluded_symbol_ids_json:
            excluded_reasons.append("Signal symbol is in the avoid symbol list.")

        if profile.market_types_json:
            if context.symbol is None:
                preference_warnings.append("Symbol market type was unavailable.")
            elif context.symbol.market_type in profile.market_types_json:
                included_reasons.append("Signal market matches preferred markets.")
            else:
                excluded_reasons.append("Signal market is outside preferred markets.")

        if profile.timeframes_json:
            if signal.timeframe in profile.timeframes_json:
                included_reasons.append("Signal timeframe matches preferred timeframes.")
            else:
                excluded_reasons.append("Signal timeframe is outside preferred timeframes.")

        if profile.session_labels_json:
            if context.market_session is None:
                preference_warnings.append("Market session context was unavailable.")
            elif context.market_session.session_label in profile.session_labels_json:
                included_reasons.append("Signal session matches preferred sessions.")
            else:
                excluded_reasons.append("Signal session is outside preferred sessions.")

        pattern_type = signal.pattern_type
        if pattern_type is not None and pattern_type in profile.excluded_pattern_types_json:
            excluded_reasons.append("Signal pattern is in the avoid pattern list.")
        if profile.pattern_types_json:
            if pattern_type is None:
                excluded_reasons.append(
                    "Signal has no pattern type for preferred pattern filtering."
                )
            elif pattern_type in profile.pattern_types_json:
                included_reasons.append("Signal pattern matches preferred patterns.")
            else:
                excluded_reasons.append("Signal pattern is outside preferred patterns.")

        if profile.strategy_profile_keys_json:
            if signal.strategy_profile_key is None:
                excluded_reasons.append("Signal has no deterministic strategy profile key.")
            elif signal.strategy_profile_key in profile.strategy_profile_keys_json:
                included_reasons.append(
                    "Signal deterministic profile matches preferred profile keys."
                )
            else:
                excluded_reasons.append(
                    "Signal deterministic profile is outside preferred profile keys."
                )

        if profile.minimum_confidence is not None:
            if signal.confidence_score >= profile.minimum_confidence:
                included_reasons.append("Signal meets the minimum confidence preference.")
            else:
                excluded_reasons.append("Signal is below the minimum confidence preference.")

        if profile.minimum_setup_quality is not None:
            if context.setup_context is None:
                excluded_reasons.append("Setup context is unavailable for minimum setup quality.")
            elif context.setup_context.setup_quality_score >= profile.minimum_setup_quality:
                included_reasons.append("Setup context meets the minimum setup quality preference.")
            else:
                excluded_reasons.append(
                    "Setup context is below the minimum setup quality preference."
                )

        self.evaluate_freshness(
            profile,
            context,
            included_reasons,
            excluded_reasons,
            preference_warnings,
        )
        self.evaluate_timeframe_agreement(
            profile,
            context,
            included_reasons,
            excluded_reasons,
            preference_warnings,
        )
        self.evaluate_data_quality(
            profile,
            context,
            included_reasons,
            excluded_reasons,
            preference_warnings,
        )

        if profile.include_news_context:
            preference_warnings.append("News context is preferred when available.")
        if profile.include_outcomes:
            preference_warnings.append("Outcome context is preferred when available.")

        if not included_reasons and not excluded_reasons:
            included_reasons.append("No restrictive preference filters were configured.")

        return PreferenceMatchResult(
            matches=not excluded_reasons,
            included_reasons=included_reasons,
            excluded_reasons=excluded_reasons,
            preference_warnings=preference_warnings,
        )

    def evaluate_freshness(
        self,
        profile: PersonalStrategyPreferenceProfile,
        context: PreferenceSignalContext,
        included_reasons: list[str],
        excluded_reasons: list[str],
        preference_warnings: list[str],
    ) -> None:
        memory = context.market_memory
        latest_time = (
            memory.latest_final_candle_time if memory is not None else context.signal.created_at
        )
        freshness_label = memory.freshness_label if memory is not None else None
        if profile.require_fresh_data:
            if freshness_label == "fresh":
                included_reasons.append("Latest market memory is marked fresh.")
            elif freshness_label is None:
                excluded_reasons.append(
                    "Freshness context is unavailable while fresh data is required."
                )
            else:
                excluded_reasons.append("Latest market memory is not marked fresh.")
        if profile.max_stale_seconds is None:
            return
        if latest_time is None:
            preference_warnings.append("Latest context time was unavailable for stale tolerance.")
            return
        evaluated_at = context.evaluated_at or utc_now()
        stale_seconds = max(0, int((evaluated_at - latest_time).total_seconds()))
        if stale_seconds <= profile.max_stale_seconds:
            included_reasons.append("Latest context is within stale data tolerance.")
        else:
            excluded_reasons.append("Latest context is outside stale data tolerance.")

    def evaluate_timeframe_agreement(
        self,
        profile: PersonalStrategyPreferenceProfile,
        context: PreferenceSignalContext,
        included_reasons: list[str],
        excluded_reasons: list[str],
        preference_warnings: list[str],
    ) -> None:
        if not profile.require_timeframe_agreement:
            return
        if context.setup_context is None:
            excluded_reasons.append("Setup context is unavailable for timeframe agreement.")
            return
        agreement = context.setup_context.timeframe_agreement_json or {}
        if timeframe_agreement_is_acceptable(agreement):
            included_reasons.append("Setup context shows acceptable timeframe agreement.")
            return
        if agreement:
            excluded_reasons.append("Setup context does not meet timeframe agreement preference.")
        else:
            preference_warnings.append("Timeframe agreement details were unavailable.")
            excluded_reasons.append("Timeframe agreement preference could not be satisfied.")

    def evaluate_data_quality(
        self,
        profile: PersonalStrategyPreferenceProfile,
        context: PreferenceSignalContext,
        included_reasons: list[str],
        excluded_reasons: list[str],
        preference_warnings: list[str],
    ) -> None:
        if not profile.require_acceptable_data_quality:
            return
        memory = context.market_memory
        if memory is None:
            preference_warnings.append("Market memory data quality context was unavailable.")
            excluded_reasons.append("Data quality preference could not be satisfied.")
            return
        if memory.data_quality_label in {"strong", "acceptable"}:
            included_reasons.append("Market memory data quality is acceptable.")
        else:
            excluded_reasons.append("Market memory data quality is below acceptable preference.")


def timeframe_agreement_is_acceptable(agreement: dict[str, object]) -> bool:
    aligned = agreement.get("isAligned")
    if isinstance(aligned, bool):
        return aligned
    score = agreement.get("agreementScore") or agreement.get("score")
    if isinstance(score, (int, float, Decimal)):
        return Decimal(str(score)) >= Decimal("0.5000")
    label = str(
        agreement.get("agreementLabel")
        or agreement.get("label")
        or agreement.get("timeframeAgreementLabel")
        or ""
    ).lower()
    if not label:
        return False
    return label in {"aligned", "confirmed", "supportive", "agreement", "acceptable"}
