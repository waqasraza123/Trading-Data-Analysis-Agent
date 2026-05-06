from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.job_queue.adapters.base import JobQueueBackend
from app.modules.job_queue.adapters.database import DatabaseJobQueueBackend
from app.modules.job_queue.adapters.redis import RedisJobQueueBackend
from app.modules.job_queue.models import (
    JobQueueDefinition,
    JobQueueDefinitionStatus,
    JobQueueEvent,
    JobQueueEventType,
    JobQueueItem,
    JobQueueItemStatus,
    JobQueueJobType,
    JobQueuePriority,
)
from app.modules.job_queue.repository import is_idempotency_integrity_error
from app.modules.job_queue.schemas import JobQueueJobCreate


@dataclass(frozen=True)
class DefaultJobQueueDefinition:
    key: str
    name: str
    description: str
    queue_name: str
    job_type: JobQueueJobType
    default_priority: JobQueuePriority = JobQueuePriority.NORMAL
    timeout_seconds: int | None = None


@dataclass(frozen=True)
class JobQueueSeedResult:
    seeded_count: int
    updated_count: int
    definition_keys: list[str]


def default_job_queue_definitions() -> list[DefaultJobQueueDefinition]:
    return [
        DefaultJobQueueDefinition(
            "import_csv",
            "CSV import",
            "Processes bounded CSV market data import work.",
            "imports",
            JobQueueJobType.IMPORT_CSV,
        ),
        DefaultJobQueueDefinition(
            "import_json",
            "JSON import",
            "Processes bounded JSON market data import work.",
            "imports",
            JobQueueJobType.IMPORT_JSON,
        ),
        DefaultJobQueueDefinition(
            "provider_polling_fetch",
            "Provider polling fetch",
            "Fetches explicit provider polling requests through backend-safe provider adapters.",
            "provider_polling",
            JobQueueJobType.PROVIDER_POLLING_FETCH,
            JobQueuePriority.HIGH,
        ),
        DefaultJobQueueDefinition(
            "scan_run",
            "Scheduled scan run",
            "Runs deterministic scans over stored candle data.",
            "scans",
            JobQueueJobType.SCAN_RUN,
            JobQueuePriority.HIGH,
        ),
        DefaultJobQueueDefinition(
            "daily_workflow_run",
            "Daily workflow run",
            "Runs bounded daily workflow orchestration over existing backend services.",
            "workflows",
            JobQueueJobType.DAILY_WORKFLOW_RUN,
            JobQueuePriority.HIGH,
        ),
        DefaultJobQueueDefinition(
            "outcome_evaluate",
            "Outcome evaluation",
            "Evaluates stored signal outcomes after configured horizons.",
            "outcomes",
            JobQueueJobType.OUTCOME_EVALUATE,
        ),
        DefaultJobQueueDefinition(
            "reasoning_generate",
            "Reasoning generation",
            "Runs grounded reasoning generation from persisted deterministic artifacts.",
            "reasoning",
            JobQueueJobType.REASONING_GENERATE,
        ),
        DefaultJobQueueDefinition(
            "notification_deliver",
            "Notification delivery",
            "Dispatches sanitized backend notification events through configured channels.",
            "notifications",
            JobQueueJobType.NOTIFICATION_DELIVER,
            JobQueuePriority.HIGH,
        ),
        DefaultJobQueueDefinition(
            "read_model_rebuild",
            "Read model rebuild",
            "Rebuilds dashboard read models from persisted deterministic artifacts.",
            "read_models",
            JobQueueJobType.READ_MODEL_REBUILD,
        ),
        DefaultJobQueueDefinition(
            "backfill_item",
            "Backfill item",
            "Processes bounded planned backfill items.",
            "backfills",
            JobQueueJobType.BACKFILL_ITEM,
            JobQueuePriority.LOW,
        ),
        DefaultJobQueueDefinition(
            "data_quality_run",
            "Data quality run",
            "Runs data quality checks over stored market data.",
            "data_quality",
            JobQueueJobType.DATA_QUALITY_RUN,
        ),
        DefaultJobQueueDefinition(
            "retention_apply",
            "Data retention apply",
            "Applies explicit data retention run items within configured safety boundaries.",
            "retention",
            JobQueueJobType.RETENTION_APPLY,
            JobQueuePriority.LOW,
        ),
        DefaultJobQueueDefinition(
            "llm_explain",
            "LLM explanation",
            "Generates grounded explanations from persisted evidence when enabled.",
            "llm",
            JobQueueJobType.LLM_EXPLAIN,
        ),
        DefaultJobQueueDefinition(
            "report_build",
            "Report build",
            "Builds read-only intelligence reports from stored artifacts.",
            "reports",
            JobQueueJobType.REPORT_BUILD,
        ),
    ]


class JobQueueService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        backend: JobQueueBackend | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.backend = backend or self.create_backend(session)

    def create_backend(self, session: AsyncSession) -> JobQueueBackend:
        if self.settings.job_queue_backend == "redis":
            return RedisJobQueueBackend(session)
        return DatabaseJobQueueBackend(session)

    async def enqueue_job(
        self,
        payload: JobQueueJobCreate,
        commit: bool = True,
    ) -> JobQueueItem:
        self.validate_job_payload(payload.job_type, payload.payload_json)
        if payload.idempotency_key is not None and not payload.force:
            existing = await self.backend.get_job_by_idempotency_key(
                payload.workspace_id,
                payload.idempotency_key,
            )
            if existing is not None:
                return existing
        definition = await self.resolve_definition(payload.job_type)
        queue_name = payload.queue_name or definition.queue_name
        priority = payload.priority or JobQueuePriority(definition.default_priority)
        max_attempts = payload.max_attempts or definition.max_attempts
        now = utc_now()
        available_at = (
            payload.scheduled_at
            if payload.scheduled_at is not None and payload.scheduled_at > now
            else now
        )
        status = (
            JobQueueItemStatus.SCHEDULED
            if payload.scheduled_at is not None and payload.scheduled_at > now
            else JobQueueItemStatus.PENDING
        )
        idempotency_key = (
            forced_key(payload.idempotency_key)
            if payload.idempotency_key is not None and payload.force
            else payload.idempotency_key
        )
        job = JobQueueItem(
            workspace_id=payload.workspace_id,
            queue_name=queue_name,
            job_type=payload.job_type.value,
            status=status.value,
            priority=priority.value,
            idempotency_key=idempotency_key,
            scheduled_at=payload.scheduled_at,
            available_at=available_at,
            attempts=0,
            max_attempts=max_attempts,
            payload_json=self.enriched_payload(payload.payload_json),
        )
        try:
            created = await self.backend.create_job(job)
            await self.add_event(
                created,
                JobQueueEventType.ENQUEUED,
                "Job enqueued",
                {"backend": self.backend.backend_name},
                commit=False,
            )
            if commit:
                await self.session.commit()
            return created
        except IntegrityError as error:
            await self.session.rollback()
            existing = (
                await self.backend.get_job_by_idempotency_key(
                    payload.workspace_id,
                    payload.idempotency_key,
                )
                if payload.idempotency_key is not None and is_idempotency_integrity_error(error)
                else None
            )
            if existing is not None and not payload.force:
                return existing
            raise AppError(
                409,
                "job_queue_idempotency_conflict",
                "Job could not be enqueued",
            ) from error

    async def get_job(self, job_id: UUID) -> JobQueueItem:
        job = await self.backend.get_job(job_id)
        if job is None:
            raise AppError(404, "job_queue_job_not_found", "Job queue item not found")
        return job

    async def list_jobs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        queue_name: str | None = None,
        job_type: JobQueueJobType | None = None,
        status: JobQueueItemStatus | None = None,
    ) -> list[JobQueueItem]:
        return await self.backend.list_jobs(
            limit=limit,
            offset=offset,
            workspace_id=workspace_id,
            queue_name=queue_name,
            job_type=job_type.value if job_type is not None else None,
            status=status.value if status is not None else None,
        )

    async def claim_jobs(
        self,
        queue_name: str,
        worker_id: str,
        limit: int | None = None,
        commit: bool = True,
    ) -> list[JobQueueItem]:
        batch_limit = min(limit or self.settings.job_queue_claim_batch_size, 500)
        jobs = await self.backend.claim_jobs(
            now=utc_now(),
            queue_name=queue_name,
            worker_id=worker_id,
            limit=batch_limit,
            lock_seconds=self.settings.job_queue_lock_seconds,
        )
        for job in jobs:
            await self.add_event(
                job,
                JobQueueEventType.CLAIMED,
                "Job claimed",
                {"workerId": worker_id, "attempts": job.attempts},
                commit=False,
            )
        if commit:
            await self.session.commit()
        return jobs

    async def heartbeat(
        self,
        job_id: UUID,
        worker_id: str,
        commit: bool = True,
    ) -> JobQueueItem:
        job = await self.get_job(job_id)
        self.ensure_worker_lock(job, worker_id)
        if job.status != JobQueueItemStatus.RUNNING.value:
            raise AppError(422, "job_queue_job_not_running", "Only running jobs can heartbeat")
        job.locked_until = utc_now() + timedelta(seconds=self.settings.job_queue_lock_seconds)
        await self.add_event(
            job,
            JobQueueEventType.HEARTBEAT,
            "Job heartbeat recorded",
            {"workerId": worker_id},
            commit=False,
        )
        updated = await self.backend.update_job(job)
        if commit:
            await self.session.commit()
        return updated

    async def start_job(
        self,
        job_id: UUID,
        worker_id: str,
        commit: bool = True,
    ) -> JobQueueItem:
        job = await self.get_job(job_id)
        self.ensure_worker_lock(job, worker_id)
        job.started_at = job.started_at or utc_now()
        await self.add_event(
            job,
            JobQueueEventType.STARTED,
            "Job started",
            {"workerId": worker_id},
            commit=False,
        )
        updated = await self.backend.update_job(job)
        if commit:
            await self.session.commit()
        return updated

    async def complete_job(
        self,
        job_id: UUID,
        result: dict[str, Any],
        completed_with_warnings: bool = False,
        commit: bool = True,
    ) -> JobQueueItem:
        job = await self.get_job(job_id)
        if job.status in terminal_statuses():
            return job
        job.status = (
            JobQueueItemStatus.COMPLETED_WITH_WARNINGS.value
            if completed_with_warnings
            else JobQueueItemStatus.COMPLETED.value
        )
        job.result_json = result
        job.error_code = None
        job.error_message = None
        job.locked_by = None
        job.locked_until = None
        job.completed_at = utc_now()
        await self.add_event(
            job,
            JobQueueEventType.COMPLETED,
            "Job completed",
            {"completedWithWarnings": completed_with_warnings},
            commit=False,
        )
        updated = await self.backend.update_job(job)
        if commit:
            await self.session.commit()
        return updated

    async def fail_job(
        self,
        job_id: UUID,
        error_code: str,
        error_message: str,
        commit: bool = True,
    ) -> JobQueueItem:
        job = await self.get_job(job_id)
        if job.status in terminal_statuses() - {JobQueueItemStatus.FAILED.value}:
            return job
        job.status = JobQueueItemStatus.FAILED.value
        job.error_code = error_code[:120]
        job.error_message = error_message[:2000]
        job.locked_by = None
        job.locked_until = None
        job.completed_at = utc_now()
        await self.add_event(
            job,
            JobQueueEventType.FAILED,
            "Job failed",
            {"errorCode": job.error_code},
            commit=False,
        )
        updated = await self.backend.update_job(job)
        if commit:
            await self.session.commit()
        return updated

    async def retry_job(
        self,
        job_id: UUID,
        commit: bool = True,
    ) -> JobQueueItem:
        job = await self.get_job(job_id)
        if job.status in completed_or_cancelled_statuses():
            raise AppError(
                422,
                "job_queue_job_not_retryable",
                "Completed or cancelled jobs cannot retry",
            )
        if job.attempts >= job.max_attempts:
            return await self.move_to_dead_letter(job.id, commit=commit)
        delay_seconds = self.settings.job_queue_retry_backoff_seconds * max(job.attempts, 1)
        job.status = JobQueueItemStatus.RETRYING.value
        job.available_at = utc_now() + timedelta(seconds=delay_seconds)
        job.locked_by = None
        job.locked_until = None
        await self.add_event(
            job,
            JobQueueEventType.RETRY_SCHEDULED,
            "Job retry scheduled",
            {"delaySeconds": delay_seconds, "attempts": job.attempts},
            commit=False,
        )
        updated = await self.backend.update_job(job)
        if commit:
            await self.session.commit()
        return updated

    async def cancel_job(
        self,
        job_id: UUID,
        reason: str | None = None,
        commit: bool = True,
    ) -> JobQueueItem:
        job = await self.get_job(job_id)
        if job.status in terminal_statuses():
            return job
        job.status = JobQueueItemStatus.CANCELLED.value
        job.locked_by = None
        job.locked_until = None
        job.completed_at = utc_now()
        await self.add_event(
            job,
            JobQueueEventType.CANCELLED,
            "Job cancelled",
            {"reason": reason} if reason else {},
            commit=False,
        )
        updated = await self.backend.update_job(job)
        if commit:
            await self.session.commit()
        return updated

    async def move_to_dead_letter(
        self,
        job_id: UUID,
        commit: bool = True,
    ) -> JobQueueItem:
        job = await self.get_job(job_id)
        if job.status in completed_or_cancelled_statuses():
            return job
        job.status = JobQueueItemStatus.DEAD_LETTER.value
        job.locked_by = None
        job.locked_until = None
        job.completed_at = utc_now()
        await self.add_event(
            job,
            JobQueueEventType.DEAD_LETTERED,
            "Job moved to dead letter",
            {"attempts": job.attempts, "maxAttempts": job.max_attempts},
            commit=False,
        )
        updated = await self.backend.update_job(job)
        if commit:
            await self.session.commit()
        return updated

    async def seed_default_job_definitions(self) -> JobQueueSeedResult:
        seeded_count = 0
        updated_count = 0
        definition_keys: list[str] = []
        for spec in default_job_queue_definitions():
            _, created = await self.backend.upsert_definition(
                JobQueueDefinition(
                    key=spec.key,
                    name=spec.name,
                    description=spec.description,
                    status=JobQueueDefinitionStatus.ACTIVE.value,
                    queue_name=spec.queue_name,
                    job_type=spec.job_type.value,
                    max_attempts=self.settings.job_queue_default_max_attempts,
                    default_priority=spec.default_priority.value,
                    timeout_seconds=spec.timeout_seconds,
                    metadata_json={"backendSafe": True},
                )
            )
            if created:
                seeded_count += 1
            else:
                updated_count += 1
            definition_keys.append(spec.key)
        await self.session.commit()
        return JobQueueSeedResult(
            seeded_count=seeded_count,
            updated_count=updated_count,
            definition_keys=definition_keys,
        )

    async def list_definitions(
        self,
        status: JobQueueDefinitionStatus | None = None,
        queue_name: str | None = None,
        job_type: JobQueueJobType | None = None,
    ) -> list[JobQueueDefinition]:
        return await self.backend.list_definitions(
            status=status.value if status is not None else None,
            queue_name=queue_name,
            job_type=job_type.value if job_type is not None else None,
        )

    async def list_events(self, job_id: UUID) -> list[JobQueueEvent]:
        await self.get_job(job_id)
        return await self.backend.list_events(job_id)

    async def resolve_definition(self, job_type: JobQueueJobType) -> JobQueueDefinition:
        definition = await self.backend.get_definition_by_job_type(job_type.value)
        if definition is None:
            spec = default_definition_for_job_type(job_type)
            return JobQueueDefinition(
                key=spec.key,
                name=spec.name,
                description=spec.description,
                status=JobQueueDefinitionStatus.ACTIVE.value,
                queue_name=spec.queue_name,
                job_type=spec.job_type.value,
                max_attempts=self.settings.job_queue_default_max_attempts,
                default_priority=spec.default_priority.value,
                timeout_seconds=spec.timeout_seconds,
                metadata_json={"implicitDefault": True, "backendSafe": True},
            )
        if definition.status != JobQueueDefinitionStatus.ACTIVE.value:
            raise AppError(
                422,
                "job_queue_definition_inactive",
                "Job queue definition is not active",
            )
        return definition

    async def add_event(
        self,
        job: JobQueueItem,
        event_type: JobQueueEventType,
        message: str,
        metadata_json: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> JobQueueEvent:
        event = await self.backend.add_event(
            JobQueueEvent(
                workspace_id=job.workspace_id,
                job_id=job.id,
                event_type=event_type.value,
                message=message,
                metadata_json=metadata_json or {},
            )
        )
        if commit:
            await self.session.commit()
        return event

    def ensure_worker_lock(self, job: JobQueueItem, worker_id: str) -> None:
        if job.locked_by != worker_id:
            raise AppError(409, "job_queue_lock_mismatch", "Job is not locked by this worker")

    def enriched_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        engine_execution_id = payload.get("engineExecutionRecordId")
        if engine_execution_id is None:
            return payload
        return {**payload, "engineExecutionRecordId": str(engine_execution_id)}

    def validate_job_payload(
        self,
        job_type: JobQueueJobType,
        payload: dict[str, Any],
    ) -> None:
        if job_type.value not in {item.value for item in JobQueueJobType}:
            raise AppError(422, "job_queue_unsupported_job_type", "Unsupported job type")
        operation_type = str(payload.get("operationType", "")).strip().lower()
        if operation_type in unsafe_operation_types():
            raise AppError(
                422,
                "job_queue_unsafe_operation_type",
                "Job payload operation type is outside backend-safe scope",
            )


def default_definition_for_job_type(job_type: JobQueueJobType) -> DefaultJobQueueDefinition:
    for definition in default_job_queue_definitions():
        if definition.job_type == job_type:
            return definition
    raise AppError(422, "job_queue_unsupported_job_type", "Unsupported job type")


def forced_key(idempotency_key: str | None) -> str | None:
    if idempotency_key is None:
        return None
    suffix = uuid4().hex
    max_prefix_length = 240 - len(":forced:") - len(suffix)
    return f"{idempotency_key[:max_prefix_length]}:forced:{suffix}"


def terminal_statuses() -> set[str]:
    return {
        JobQueueItemStatus.COMPLETED.value,
        JobQueueItemStatus.COMPLETED_WITH_WARNINGS.value,
        JobQueueItemStatus.FAILED.value,
        JobQueueItemStatus.CANCELLED.value,
        JobQueueItemStatus.DEAD_LETTER.value,
    }


def completed_or_cancelled_statuses() -> set[str]:
    return {
        JobQueueItemStatus.COMPLETED.value,
        JobQueueItemStatus.COMPLETED_WITH_WARNINGS.value,
        JobQueueItemStatus.CANCELLED.value,
    }


def unsafe_operation_types() -> set[str]:
    return {
        "broker.execute",
        "broker.order",
        "order.place",
        "order.execute",
        "trade.execute",
        "auto_trade",
        "auto-trade",
    }
