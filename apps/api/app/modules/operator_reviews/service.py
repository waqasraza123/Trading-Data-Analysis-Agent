from importlib import import_module
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.operator_reviews.models import (
    OperatorReviewEvent,
    OperatorReviewEventType,
    OperatorReviewItem,
    OperatorReviewPriority,
    OperatorReviewResolution,
    OperatorReviewSourceType,
    OperatorReviewStatus,
    OperatorReviewType,
)
from app.modules.operator_reviews.repository import OperatorReviewRepository
from app.modules.operator_reviews.schemas import (
    OperatorReviewCreateRequest,
    OperatorReviewEventRead,
    OperatorReviewItemRead,
)


class OperatorReviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = OperatorReviewRepository(session)

    async def create_review_item(
        self,
        payload: OperatorReviewCreateRequest,
    ) -> OperatorReviewItemRead:
        if not payload.force_create:
            existing = await self.repository.find_active_by_source(
                workspace_id=payload.workspace_id,
                source_type=payload.source_type.value,
                source_id=payload.source_id,
                review_type=payload.review_type.value,
            )
            if existing is not None:
                return OperatorReviewItemRead.model_validate(existing)
        try:
            item = await self.repository.create_item(
                OperatorReviewItem(
                    workspace_id=payload.workspace_id,
                    source_type=payload.source_type.value,
                    source_id=payload.source_id,
                    related_analysis_run_id=payload.related_analysis_run_id,
                    related_signal_id=payload.related_signal_id,
                    related_reasoning_run_id=payload.related_reasoning_run_id,
                    related_action_item_id=payload.related_action_item_id,
                    review_type=payload.review_type.value,
                    priority=payload.priority.value,
                    status=(
                        OperatorReviewStatus.ASSIGNED.value
                        if payload.assigned_to_user_id is not None
                        else OperatorReviewStatus.OPEN.value
                    ),
                    title=payload.title,
                    summary=payload.summary,
                    reason_code=payload.reason_code,
                    evidence_json=payload.evidence_json,
                    assigned_to_user_id=payload.assigned_to_user_id,
                    created_by_user_id=payload.created_by_user_id,
                    metadata_json=payload.metadata_json,
                )
            )
        except IntegrityError:
            if payload.force_create:
                raise
            await self.session.rollback()
            existing_after_race = await self.repository.find_active_by_source(
                workspace_id=payload.workspace_id,
                source_type=payload.source_type.value,
                source_id=payload.source_id,
                review_type=payload.review_type.value,
            )
            if existing_after_race is None:
                raise
            return OperatorReviewItemRead.model_validate(existing_after_race)
        await self.add_review_event(
            review_item_id=item.id,
            event_type=OperatorReviewEventType.CREATED,
            message="Review item created",
            user_id=payload.created_by_user_id,
            metadata_json={
                "sourceType": payload.source_type.value,
                "sourceId": str(payload.source_id),
                "reviewType": payload.review_type.value,
            },
            commit=False,
        )
        if payload.assigned_to_user_id is not None:
            await self.add_review_event(
                review_item_id=item.id,
                event_type=OperatorReviewEventType.ASSIGNED,
                message="Review item assigned",
                user_id=payload.created_by_user_id,
                metadata_json={"assignedToUserId": str(payload.assigned_to_user_id)},
                commit=False,
            )
        await self.session.commit()
        await self.session.refresh(item)
        return OperatorReviewItemRead.model_validate(item)

    async def list_review_items(
        self,
        workspace_id: UUID,
        status: OperatorReviewStatus | None = None,
        priority: OperatorReviewPriority | None = None,
        review_type: OperatorReviewType | None = None,
        source_type: OperatorReviewSourceType | None = None,
        assigned_to_user_id: UUID | None = None,
        related_signal_id: UUID | None = None,
        related_analysis_run_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[OperatorReviewItemRead]:
        items = await self.repository.list_items(
            workspace_id=workspace_id,
            status=status.value if status is not None else None,
            priority=priority.value if priority is not None else None,
            review_type=review_type.value if review_type is not None else None,
            source_type=source_type.value if source_type is not None else None,
            assigned_to_user_id=assigned_to_user_id,
            related_signal_id=related_signal_id,
            related_analysis_run_id=related_analysis_run_id,
            limit=limit,
            offset=offset,
        )
        return [OperatorReviewItemRead.model_validate(item) for item in items]

    async def get_review_item(self, review_item_id: UUID) -> OperatorReviewItemRead:
        item = await self.get_item_or_raise(review_item_id)
        return OperatorReviewItemRead.model_validate(item)

    async def assign_review_item(
        self,
        review_item_id: UUID,
        user_id: UUID,
        actor_user_id: UUID | None = None,
    ) -> OperatorReviewItemRead:
        item = await self.get_item_or_raise(review_item_id)
        self.ensure_active(item)
        item.assigned_to_user_id = user_id
        if item.status == OperatorReviewStatus.OPEN.value:
            item.status = OperatorReviewStatus.ASSIGNED.value
        await self.repository.update_item(item)
        await self.add_review_event(
            review_item_id=item.id,
            event_type=OperatorReviewEventType.ASSIGNED,
            message="Review item assigned",
            user_id=actor_user_id,
            metadata_json={"assignedToUserId": str(user_id)},
            commit=False,
        )
        await self.session.commit()
        await self.session.refresh(item)
        return OperatorReviewItemRead.model_validate(item)

    async def update_review_status(
        self,
        review_item_id: UUID,
        status: OperatorReviewStatus,
        actor_user_id: UUID | None = None,
        notes: str | None = None,
    ) -> OperatorReviewItemRead:
        if status == OperatorReviewStatus.RESOLVED:
            raise AppError(422, "use_resolve_endpoint", "Use the resolve endpoint for resolutions")
        if status == OperatorReviewStatus.DISMISSED:
            raise AppError(422, "use_dismiss_endpoint", "Use the dismiss endpoint for dismissals")
        item = await self.get_item_or_raise(review_item_id)
        prior_status = item.status
        if prior_status in {
            OperatorReviewStatus.RESOLVED.value,
            OperatorReviewStatus.DISMISSED.value,
            OperatorReviewStatus.CANCELLED.value,
        }:
            raise AppError(409, "review_item_closed", "Review item is already closed")
        item.status = status.value
        await self.repository.update_item(item)
        await self.add_review_event(
            review_item_id=item.id,
            event_type=OperatorReviewEventType.STATUS_CHANGED,
            message=notes or "Review item status changed",
            user_id=actor_user_id,
            metadata_json={"fromStatus": prior_status, "toStatus": status.value},
            commit=False,
        )
        await self.session.commit()
        await self.session.refresh(item)
        return OperatorReviewItemRead.model_validate(item)

    async def resolve_review_item(
        self,
        review_item_id: UUID,
        resolution: OperatorReviewResolution,
        notes: str | None = None,
        reviewed_by_user_id: UUID | None = None,
    ) -> OperatorReviewItemRead:
        item = await self.get_item_or_raise(review_item_id)
        self.ensure_active(item)
        item.status = OperatorReviewStatus.RESOLVED.value
        item.resolution = resolution.value
        item.resolution_notes = notes
        item.reviewed_by_user_id = reviewed_by_user_id
        item.reviewed_at = utc_now()
        await self.repository.update_item(item)
        event_type = (
            OperatorReviewEventType.ESCALATED
            if resolution == OperatorReviewResolution.ESCALATED
            else OperatorReviewEventType.RESOLVED
        )
        await self.add_review_event(
            review_item_id=item.id,
            event_type=event_type,
            message=notes or "Review item resolved",
            user_id=reviewed_by_user_id,
            metadata_json={"resolution": resolution.value},
            commit=False,
        )
        await self.session.commit()
        await self.session.refresh(item)
        return OperatorReviewItemRead.model_validate(item)

    async def dismiss_review_item(
        self,
        review_item_id: UUID,
        notes: str | None = None,
        reviewed_by_user_id: UUID | None = None,
    ) -> OperatorReviewItemRead:
        item = await self.get_item_or_raise(review_item_id)
        self.ensure_active(item)
        item.status = OperatorReviewStatus.DISMISSED.value
        item.resolution = OperatorReviewResolution.DISMISSED.value
        item.resolution_notes = notes
        item.reviewed_by_user_id = reviewed_by_user_id
        item.reviewed_at = utc_now()
        await self.repository.update_item(item)
        await self.add_review_event(
            review_item_id=item.id,
            event_type=OperatorReviewEventType.DISMISSED,
            message=notes or "Review item dismissed",
            user_id=reviewed_by_user_id,
            metadata_json={"resolution": OperatorReviewResolution.DISMISSED.value},
            commit=False,
        )
        await self.session.commit()
        await self.session.refresh(item)
        return OperatorReviewItemRead.model_validate(item)

    async def add_review_event(
        self,
        review_item_id: UUID,
        event_type: OperatorReviewEventType,
        message: str,
        user_id: UUID | None = None,
        metadata_json: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> OperatorReviewEventRead:
        item = await self.get_item_or_raise(review_item_id)
        event = await self.repository.create_event(
            OperatorReviewEvent(
                workspace_id=item.workspace_id,
                review_item_id=item.id,
                event_type=event_type.value,
                user_id=user_id,
                message=message,
                metadata_json=metadata_json or {},
            )
        )
        if commit:
            await self.session.commit()
            await self.session.refresh(event)
        return OperatorReviewEventRead.model_validate(event)

    async def list_review_events(self, review_item_id: UUID) -> list[OperatorReviewEventRead]:
        await self.get_item_or_raise(review_item_id)
        events = await self.repository.list_events(review_item_id)
        return [OperatorReviewEventRead.model_validate(event) for event in events]

    async def create_from_action_item(
        self,
        action_item_id: UUID,
        force_create: bool = False,
    ) -> OperatorReviewItemRead:
        action_item = await self.optional_get(
            "app.modules.action_plans.models",
            "ReasoningActionItem",
            action_item_id,
        )
        return await self.create_review_item(
            OperatorReviewCreateRequest(
                workspace_id=action_item.workspace_id,
                source_type=OperatorReviewSourceType.ACTION_ITEM,
                source_id=action_item.id,
                review_type=OperatorReviewType.ACTION_REVIEW,
                priority=priority_from_source(getattr(action_item, "priority", None)),
                title="Review action item",
                summary="Action item requested human review.",
                reason_code="request_human_review",
                evidence_json={
                    "actionType": getattr(action_item, "action_type", None),
                    "status": getattr(action_item, "status", None),
                    "input": getattr(action_item, "input_json", {}),
                },
                related_analysis_run_id=getattr(action_item, "analysis_run_id", None),
                related_signal_id=getattr(action_item, "signal_id", None),
                related_reasoning_run_id=getattr(action_item, "reasoning_run_id", None),
                related_action_item_id=action_item.id,
                force_create=force_create,
            )
        )

    async def create_from_calibration_recommendation(
        self,
        recommendation_id: UUID,
        force_create: bool = False,
    ) -> OperatorReviewItemRead:
        recommendation = await self.optional_get(
            "app.modules.profile_diagnostics.models",
            "CalibrationRecommendation",
            recommendation_id,
        )
        return await self.create_review_item(
            OperatorReviewCreateRequest(
                workspace_id=recommendation.workspace_id,
                source_type=OperatorReviewSourceType.CALIBRATION_RECOMMENDATION,
                source_id=recommendation.id,
                review_type=OperatorReviewType.CALIBRATION_REVIEW,
                priority=priority_from_severity(getattr(recommendation, "severity", None)),
                title=getattr(recommendation, "title", "Review calibration recommendation"),
                summary=getattr(
                    recommendation,
                    "rationale",
                    "Calibration recommendation needs review.",
                ),
                reason_code=getattr(recommendation, "recommendation_type", None),
                evidence_json=getattr(recommendation, "evidence_json", {}),
                force_create=force_create,
            )
        )

    async def create_from_chart_screenshot_run(
        self,
        run_id: UUID,
        force_create: bool = False,
    ) -> OperatorReviewItemRead:
        run = await self.optional_get(
            "app.modules.chart_screenshots.models",
            "ChartScreenshotRun",
            run_id,
        )
        return await self.create_review_item(
            OperatorReviewCreateRequest(
                workspace_id=run.workspace_id,
                source_type=OperatorReviewSourceType.CHART_SCREENSHOT_RUN,
                source_id=run.id,
                review_type=OperatorReviewType.EXTRACTION_QUALITY,
                priority=OperatorReviewPriority.HIGH,
                title="Review chart screenshot extraction",
                summary="Chart screenshot extraction requires operator review before analysis.",
                reason_code=getattr(run, "analysis_blocked_reason", None)
                or getattr(run, "last_error_code", None),
                evidence_json={
                    "status": getattr(run, "status", None),
                    "extractionConfidence": str(getattr(run, "extraction_confidence", "")),
                    "warnings": getattr(run, "extraction_warnings_json", {}),
                    "parserMetadata": getattr(run, "parser_metadata_json", {}),
                },
                related_analysis_run_id=getattr(run, "analysis_run_id", None),
                force_create=force_create,
            )
        )

    async def create_from_reasoning_run(
        self,
        reasoning_run_id: UUID,
        force_create: bool = False,
    ) -> OperatorReviewItemRead:
        run = await self.optional_get(
            "app.modules.reasoning.models",
            "LlmReasoningRun",
            reasoning_run_id,
        )
        return await self.create_review_item(
            OperatorReviewCreateRequest(
                workspace_id=run.workspace_id,
                source_type=OperatorReviewSourceType.REASONING_RUN,
                source_id=run.id,
                review_type=OperatorReviewType.UNSAFE_LLM_OUTPUT,
                priority=OperatorReviewPriority.HIGH,
                title="Review unsafe or blocked reasoning output",
                summary="Reasoning run was blocked or flagged by safety/grounding checks.",
                reason_code=getattr(run, "safety_status", None),
                evidence_json={
                    "status": getattr(run, "status", None),
                    "safetyStatus": getattr(run, "safety_status", None),
                    "groundingStatus": getattr(run, "grounding_status", None),
                    "blockedTerms": getattr(run, "blocked_terms_json", []),
                    "groundingIssues": getattr(run, "grounding_issues_json", []),
                    "errorMessage": getattr(run, "error_message", None),
                },
                related_analysis_run_id=getattr(run, "analysis_run_id", None),
                related_signal_id=getattr(run, "signal_id", None),
                related_reasoning_run_id=run.id,
                force_create=force_create,
            )
        )

    async def create_from_quality_finding(
        self,
        finding_id: UUID,
        force_create: bool = False,
    ) -> OperatorReviewItemRead:
        _ = (finding_id, force_create)
        raise AppError(422, "unsupported_source_type", "Quality finding source is unavailable")

    async def get_item_or_raise(self, review_item_id: UUID) -> OperatorReviewItem:
        item = await self.repository.get_item(review_item_id)
        if item is None:
            raise AppError(404, "operator_review_not_found", "Operator review item not found")
        return item

    async def optional_get(self, module_name: str, model_name: str, item_id: UUID) -> Any:
        try:
            module = import_module(module_name)
            model = getattr(module, model_name)
        except (ImportError, AttributeError) as error:
            raise AppError(422, "unsupported_source_type", "Review source is unavailable") from error
        item = await self.session.get(model, item_id)
        if item is None:
            raise AppError(404, "review_source_not_found", "Review source not found")
        return item

    def ensure_active(self, item: OperatorReviewItem) -> None:
        if item.status not in {
            OperatorReviewStatus.OPEN.value,
            OperatorReviewStatus.ASSIGNED.value,
            OperatorReviewStatus.IN_REVIEW.value,
        }:
            raise AppError(409, "review_item_closed", "Review item is already closed")


def priority_from_source(value: object) -> OperatorReviewPriority:
    if value == OperatorReviewPriority.HIGH.value:
        return OperatorReviewPriority.HIGH
    if value == OperatorReviewPriority.LOW.value:
        return OperatorReviewPriority.LOW
    return OperatorReviewPriority.NORMAL


def priority_from_severity(value: object) -> OperatorReviewPriority:
    if value == "high":
        return OperatorReviewPriority.HIGH
    if value == "medium":
        return OperatorReviewPriority.NORMAL
    if value == "low":
        return OperatorReviewPriority.LOW
    return OperatorReviewPriority.NORMAL
