from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from app.core.time import utc_now
from app.modules.data_retention.models import (
    DataRetentionActionType,
    DataRetentionTargetType,
)
from app.modules.data_retention.schemas import DataRetentionPolicyDocument


@dataclass(frozen=True)
class PlannedRetentionAction:
    target_type: DataRetentionTargetType
    target_id: UUID
    action_type: DataRetentionActionType
    reason: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class RetentionTargetPlan:
    target_type: DataRetentionTargetType
    action_type: DataRetentionActionType
    cutoff: datetime
    reason: str
    metadata: dict[str, object]


class DataRetentionPlanner:
    def build_target_plans(
        self,
        policy: DataRetentionPolicyDocument,
        target_types: set[DataRetentionTargetType] | None = None,
        older_than: datetime | None = None,
    ) -> list[RetentionTargetPlan]:
        requested_targets = target_types or set(DataRetentionTargetType)
        now = utc_now()
        plans = [
            self._plan(
                DataRetentionTargetType.IMPORT_BATCH,
                DataRetentionActionType.ARCHIVE,
                policy.import_batch_retention_days,
                "import batch is older than retention window",
                "importBatchRetentionDays",
                now,
                older_than,
            ),
            self._plan(
                DataRetentionTargetType.LIVE_FEED_EVENT,
                DataRetentionActionType.REDACT_PAYLOAD,
                policy.live_event_payload_retention_days,
                "live feed raw payload is older than retention window",
                "liveEventPayloadRetentionDays",
                now,
                older_than,
            ),
            self._plan(
                DataRetentionTargetType.PROVIDER_POLLING_REQUEST,
                DataRetentionActionType.REDACT_PAYLOAD,
                policy.provider_polling_payload_retention_days,
                "provider polling payload is older than retention window",
                "providerPollingPayloadRetentionDays",
                now,
                older_than,
            ),
            self._plan(
                DataRetentionTargetType.LLM_EXPLANATION_PAYLOAD,
                DataRetentionActionType.REDACT_PAYLOAD,
                min(policy.llm_input_retention_days, policy.llm_output_retention_days),
                "LLM raw input or output is older than retention window",
                "llmInputRetentionDays,llmOutputRetentionDays",
                now,
                older_than,
            ),
            self._plan(
                DataRetentionTargetType.REASONING_RUN_PAYLOAD,
                DataRetentionActionType.REDACT_PAYLOAD,
                min(policy.llm_input_retention_days, policy.llm_output_retention_days),
                "reasoning run raw input or output is older than retention window",
                "llmInputRetentionDays,llmOutputRetentionDays",
                now,
                older_than,
            ),
            self._plan(
                DataRetentionTargetType.DATASET_EXPORT,
                DataRetentionActionType.DELETE_RAW_PAYLOAD,
                policy.dataset_export_retention_days,
                "dataset export payload is older than retention window",
                "datasetExportRetentionDays",
                now,
                older_than,
            ),
            self._plan(
                DataRetentionTargetType.WEBHOOK_OUTBOX_EVENT,
                DataRetentionActionType.REDACT_PAYLOAD,
                policy.webhook_outbox_retention_days,
                "webhook outbox payload is older than retention window",
                "webhookOutboxRetentionDays",
                now,
                older_than,
            ),
            self._plan(
                DataRetentionTargetType.CHART_SCREENSHOT_AUDIT_PAYLOAD,
                DataRetentionActionType.REDACT_PAYLOAD,
                policy.chart_ocr_payload_retention_days,
                "chart screenshot OCR payload is older than retention window",
                "chartOcrPayloadRetentionDays",
                now,
                older_than,
            ),
        ]
        return [plan for plan in plans if plan.target_type in requested_targets]

    def _plan(
        self,
        target_type: DataRetentionTargetType,
        action_type: DataRetentionActionType,
        retention_days: int,
        reason: str,
        policy_field: str,
        now: datetime,
        older_than: datetime | None,
    ) -> RetentionTargetPlan:
        policy_cutoff = now - timedelta(days=retention_days)
        cutoff = min(policy_cutoff, older_than) if older_than is not None else policy_cutoff
        return RetentionTargetPlan(
            target_type=target_type,
            action_type=action_type,
            cutoff=cutoff,
            reason=reason,
            metadata={
                "policyField": policy_field,
                "retentionDays": retention_days,
                "cutoff": cutoff.isoformat(),
            },
        )
