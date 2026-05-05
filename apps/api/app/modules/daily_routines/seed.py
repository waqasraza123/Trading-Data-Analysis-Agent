from app.modules.daily_routines.models import (
    DailyRoutineStepKey,
    DailyRoutineTemplate,
    DailyRoutineTemplateStatus,
    DailyRoutineType,
)


def default_daily_routine_templates(routine_version: str) -> tuple[DailyRoutineTemplate, ...]:
    return (
        build_template(
            routine_version,
            key="pre_market_scan",
            name="Pre-market scan",
            description=(
                "Refreshes data health, prepares deterministic gap recovery context, runs "
                "bounded scans, and builds review summaries before the main session."
            ),
            routine_type=DailyRoutineType.PRE_MARKET,
            steps=[
                step(DailyRoutineStepKey.PROVIDER_HEALTH_REFRESH),
                step(DailyRoutineStepKey.GAP_RECOVERY_PREPARE),
                step(DailyRoutineStepKey.SCHEDULED_SCAN_RUN),
                step(DailyRoutineStepKey.SETUP_CONTEXT_GENERATE),
                step(DailyRoutineStepKey.SIGNAL_PRIORITY_SCORE),
                step(DailyRoutineStepKey.MARKET_MEMORY_REFRESH),
                step(DailyRoutineStepKey.DIGEST_GENERATE),
                step(DailyRoutineStepKey.BRIEF_GENERATE),
            ],
            filters={"routineScope": "pre_market"},
            schedule={"preferredLocalTime": "06:30", "cadence": "daily"},
        ),
        build_template(
            routine_version,
            key="london_open_review",
            name="London open review",
            description=(
                "Runs a bounded London-session deterministic review over configured watchlists, "
                "setup context, priority scoring, memory, digest, and brief context."
            ),
            routine_type=DailyRoutineType.SESSION_OPEN,
            steps=[
                step(DailyRoutineStepKey.PROVIDER_HEALTH_REFRESH),
                step(DailyRoutineStepKey.SCHEDULED_SCAN_RUN, input_json={"sessionLabel": "london"}),
                step(DailyRoutineStepKey.SETUP_CONTEXT_GENERATE),
                step(DailyRoutineStepKey.SIGNAL_PRIORITY_SCORE),
                step(DailyRoutineStepKey.MARKET_MEMORY_REFRESH),
                step(
                    DailyRoutineStepKey.DIGEST_GENERATE,
                    input_json={"digestType": "session", "sessionLabel": "london"},
                ),
                step(
                    DailyRoutineStepKey.BRIEF_GENERATE,
                    input_json={"briefType": "session", "sessionLabel": "london"},
                ),
            ],
            filters={"sessionLabels": ["london", "overlap"]},
            schedule={"preferredLocalTime": "08:00", "cadence": "market_session"},
        ),
        build_template(
            routine_version,
            key="new_york_open_review",
            name="New York open review",
            description=(
                "Runs a bounded New York-session deterministic review over configured "
                "watchlists, setup context, priority scoring, memory, digest, and brief context."
            ),
            routine_type=DailyRoutineType.SESSION_OPEN,
            steps=[
                step(DailyRoutineStepKey.PROVIDER_HEALTH_REFRESH),
                step(
                    DailyRoutineStepKey.SCHEDULED_SCAN_RUN,
                    input_json={"sessionLabel": "new_york"},
                ),
                step(DailyRoutineStepKey.SETUP_CONTEXT_GENERATE),
                step(DailyRoutineStepKey.SIGNAL_PRIORITY_SCORE),
                step(DailyRoutineStepKey.MARKET_MEMORY_REFRESH),
                step(
                    DailyRoutineStepKey.DIGEST_GENERATE,
                    input_json={"digestType": "session", "sessionLabel": "new_york"},
                ),
                step(
                    DailyRoutineStepKey.BRIEF_GENERATE,
                    input_json={"briefType": "session", "sessionLabel": "new_york"},
                ),
            ],
            filters={"sessionLabels": ["new_york", "overlap"]},
            schedule={"preferredLocalTime": "13:30", "cadence": "market_session"},
        ),
        build_template(
            routine_version,
            key="crypto_24h_review",
            name="Crypto 24h review",
            description=(
                "Reviews continuous crypto context using provider health, bounded scans, "
                "priority scoring, market memory, digest, and brief generation."
            ),
            routine_type=DailyRoutineType.INTRADAY,
            steps=[
                step(DailyRoutineStepKey.PROVIDER_HEALTH_REFRESH),
                step(DailyRoutineStepKey.GAP_RECOVERY_PREPARE),
                step(DailyRoutineStepKey.SCHEDULED_SCAN_RUN),
                step(DailyRoutineStepKey.SIGNAL_PRIORITY_SCORE),
                step(DailyRoutineStepKey.MARKET_MEMORY_REFRESH),
                step(
                    DailyRoutineStepKey.DIGEST_GENERATE,
                    input_json={"digestType": "custom_period"},
                ),
                step(DailyRoutineStepKey.BRIEF_GENERATE, input_json={"briefType": "intraday"}),
            ],
            filters={"marketTypes": ["crypto"], "timeframes": ["15m", "1h"]},
            schedule={"cadence": "rolling_24h", "preferredLocalTime": "00:00"},
        ),
        build_template(
            routine_version,
            key="close_of_day_review",
            name="Close-of-day review",
            description=(
                "Builds end-of-day digest and brief context, then collects outcome and "
                "journal follow-up summaries."
            ),
            routine_type=DailyRoutineType.CLOSE_OF_DAY,
            steps=[
                step(DailyRoutineStepKey.PROVIDER_HEALTH_REFRESH),
                step(DailyRoutineStepKey.MARKET_MEMORY_REFRESH),
                step(DailyRoutineStepKey.DIGEST_GENERATE),
                step(DailyRoutineStepKey.BRIEF_GENERATE),
                step(DailyRoutineStepKey.OUTCOME_REVIEW_COLLECT),
                step(DailyRoutineStepKey.JOURNAL_FOLLOW_UP_COLLECT),
            ],
            filters={"routineScope": "close_of_day"},
            schedule={"preferredLocalTime": "21:30", "cadence": "daily"},
        ),
        build_template(
            routine_version,
            key="stale_data_repair",
            name="Stale data repair",
            description=(
                "Refreshes provider health, prepares gap recovery plans, and refreshes market "
                "memory for stale or missing data review."
            ),
            routine_type=DailyRoutineType.DATA_REPAIR,
            steps=[
                step(DailyRoutineStepKey.PROVIDER_HEALTH_REFRESH, required=True),
                step(DailyRoutineStepKey.GAP_RECOVERY_PREPARE),
                step(DailyRoutineStepKey.MARKET_MEMORY_REFRESH),
                step(DailyRoutineStepKey.BRIEF_GENERATE, input_json={"briefType": "watchlist"}),
            ],
            filters={"freshnessLabels": ["delayed", "no_data"], "repairOnly": True},
            schedule={"cadence": "as_needed"},
        ),
        build_template(
            routine_version,
            key="outcome_review",
            name="Outcome review",
            description=(
                "Collects recently evaluated outcome context and creates a read-only review "
                "summary."
            ),
            routine_type=DailyRoutineType.REVIEW,
            steps=[
                step(DailyRoutineStepKey.OUTCOME_REVIEW_COLLECT, required=True),
                step(
                    DailyRoutineStepKey.DIGEST_GENERATE,
                    input_json={"digestType": "custom_period"},
                ),
                step(DailyRoutineStepKey.JOURNAL_FOLLOW_UP_COLLECT),
            ],
            filters={"routineScope": "outcome_review"},
            schedule={"cadence": "daily"},
        ),
        build_template(
            routine_version,
            key="quality_review",
            name="Quality review",
            description=(
                "Collects deterministic quality diagnostics and recent readiness context for "
                "operator review."
            ),
            routine_type=DailyRoutineType.REVIEW,
            steps=[
                step(DailyRoutineStepKey.QUALITY_SUMMARY_COLLECT, required=True),
                step(DailyRoutineStepKey.MARKET_MEMORY_REFRESH),
                step(DailyRoutineStepKey.BRIEF_GENERATE, input_json={"briefType": "intraday"}),
            ],
            filters={"routineScope": "quality_review"},
            schedule={"cadence": "daily"},
        ),
        build_template(
            routine_version,
            key="journal_follow_up",
            name="Journal follow-up",
            description=(
                "Collects saved journal entries, deterministic reflection state, and missing "
                "follow-up context without changing signals or outcomes."
            ),
            routine_type=DailyRoutineType.REVIEW,
            steps=[
                step(DailyRoutineStepKey.JOURNAL_FOLLOW_UP_COLLECT, required=True),
                step(DailyRoutineStepKey.OUTCOME_REVIEW_COLLECT),
            ],
            filters={"routineScope": "journal_follow_up"},
            schedule={"cadence": "daily"},
        ),
    )


def build_template(
    routine_version: str,
    *,
    key: str,
    name: str,
    description: str,
    routine_type: DailyRoutineType,
    steps: list[dict[str, object]],
    filters: dict[str, object],
    schedule: dict[str, object],
) -> DailyRoutineTemplate:
    return DailyRoutineTemplate(
        workspace_id=None,
        key=key,
        name=name,
        description=description,
        status=DailyRoutineTemplateStatus.ACTIVE.value,
        routine_version=routine_version,
        routine_type=routine_type.value,
        steps_json=steps,
        default_filters_json=filters,
        schedule_hint_json=schedule,
        metadata_json={
            "deterministicOnly": True,
            "boundedRoutine": True,
            "noBrokerExecution": True,
            "noAutoTrading": True,
            "noFinancialAdvice": True,
            "externalNotificationsDefault": False,
            "notificationEventsRequireExplicitEnablement": True,
        },
    )


def step(
    step_key: DailyRoutineStepKey,
    *,
    required: bool = False,
    input_json: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "stepKey": step_key.value,
        "required": required,
        "inputJson": input_json or {},
    }
