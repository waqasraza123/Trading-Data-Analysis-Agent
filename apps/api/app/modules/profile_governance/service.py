from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.profile_governance.diff import diff_profile_config, strategy_profile_config
from app.modules.profile_governance.models import (
    StrategyProfileDraft,
    StrategyProfileDraftEvent,
    StrategyProfileDraftEventType,
    StrategyProfileDraftStatus,
    StrategyProfileDraftValidationStatus,
)
from app.modules.profile_governance.repository import StrategyProfileDraftRepository
from app.modules.profile_governance.schemas import (
    StrategyProfileDraftCreate,
    StrategyProfileDraftPromotionRequest,
    StrategyProfileDraftUpdate,
    StrategyProfileDraftWorkflowRequest,
)
from app.modules.profile_governance.validator import validate_profile_config
from app.modules.strategy_profiles.models import StrategyProfile

EDITABLE_STATUSES = {
    StrategyProfileDraftStatus.DRAFT.value,
    StrategyProfileDraftStatus.READY_FOR_REVIEW.value,
    StrategyProfileDraftStatus.REJECTED.value,
}


class StrategyProfileGovernanceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = StrategyProfileDraftRepository(session)

    async def create_draft(self, payload: StrategyProfileDraftCreate) -> StrategyProfileDraft:
        base_profile = await self.resolve_base_profile(
            base_strategy_profile_id=payload.base_strategy_profile_id,
            base_strategy_profile_key=payload.base_strategy_profile_key,
            base_strategy_profile_version=payload.base_strategy_profile_version,
        )
        draft = StrategyProfileDraft(
            workspace_id=payload.workspace_id,
            base_strategy_profile_id=base_profile.id if base_profile is not None else None,
            base_strategy_profile_key=payload.base_strategy_profile_key,
            base_strategy_profile_version=(
                base_profile.version
                if base_profile is not None
                else payload.base_strategy_profile_version
            ),
            draft_key=payload.draft_key,
            draft_version=payload.draft_version,
            status=StrategyProfileDraftStatus.DRAFT.value,
            name=payload.name,
            description=payload.description,
            proposed_config_json=payload.proposed_config_json,
            validation_status=StrategyProfileDraftValidationStatus.NOT_VALIDATED.value,
            validation_errors_json=[],
            validation_warnings_json=[],
            diff_json=diff_profile_config(
                strategy_profile_config(base_profile),
                payload.proposed_config_json,
            ),
            simulation_run_id=payload.simulation_run_id,
            diagnostic_run_id=payload.diagnostic_run_id,
            created_by_user_id=payload.created_by_user_id,
        )
        draft = await self.repository.create_draft(draft)
        await self.add_draft_event(
            draft=draft,
            event_type=StrategyProfileDraftEventType.CREATED,
            user_id=payload.created_by_user_id,
            message="Strategy profile draft created",
            metadata_json={
                "baseStrategyProfileId": str(draft.base_strategy_profile_id)
                if draft.base_strategy_profile_id is not None
                else None,
                "baseStrategyProfileKey": draft.base_strategy_profile_key,
                "baseStrategyProfileVersion": draft.base_strategy_profile_version,
            },
        )
        await self.session.commit()
        return draft

    async def validate_draft(self, draft_id: UUID) -> StrategyProfileDraft:
        draft = await self.get_draft(draft_id)
        await self.refresh_validation_and_diff(draft)
        await self.add_draft_event(
            draft=draft,
            event_type=StrategyProfileDraftEventType.VALIDATED,
            user_id=None,
            message="Strategy profile draft validated",
            metadata_json={
                "validationStatus": draft.validation_status,
                "errorCount": len(draft.validation_errors_json),
                "warningCount": len(draft.validation_warnings_json),
            },
        )
        draft = await self.repository.update_draft(draft)
        await self.session.commit()
        return draft

    async def get_draft(self, draft_id: UUID) -> StrategyProfileDraft:
        draft = await self.repository.get_draft(draft_id)
        if draft is None:
            raise AppError(
                404, "strategy_profile_draft_not_found", "Strategy profile draft not found"
            )
        return draft

    async def list_drafts(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        status: StrategyProfileDraftStatus | None = None,
        draft_key: str | None = None,
        base_strategy_profile_key: str | None = None,
    ) -> list[StrategyProfileDraft]:
        return await self.repository.list_drafts(
            limit=limit,
            offset=offset,
            workspace_id=workspace_id,
            status=status.value if status is not None else None,
            draft_key=draft_key,
            base_strategy_profile_key=base_strategy_profile_key,
        )

    async def update_draft(
        self,
        draft_id: UUID,
        payload: StrategyProfileDraftUpdate,
    ) -> StrategyProfileDraft:
        draft = await self.get_draft(draft_id)
        if draft.status not in EDITABLE_STATUSES:
            raise AppError(
                409,
                "strategy_profile_draft_not_editable",
                "Only draft, ready-for-review, or rejected profile drafts can be updated",
            )
        values = payload.model_dump(exclude_unset=True)
        config_changed = "proposed_config_json" in values
        for field_name in (
            "name",
            "description",
            "simulation_run_id",
            "diagnostic_run_id",
            "review_notes",
        ):
            if field_name in values:
                setattr(draft, field_name, values[field_name])
        if config_changed:
            draft.proposed_config_json = payload.proposed_config_json or {}
            draft.validation_status = StrategyProfileDraftValidationStatus.NOT_VALIDATED.value
            draft.validation_errors_json = []
            draft.validation_warnings_json = []
            draft.status = StrategyProfileDraftStatus.DRAFT.value
        await self.refresh_diff(draft)
        draft = await self.repository.update_draft(draft)
        await self.add_draft_event(
            draft=draft,
            event_type=StrategyProfileDraftEventType.NOTE_ADDED,
            user_id=payload.user_id,
            message="Strategy profile draft updated",
            metadata_json={"configChanged": config_changed},
        )
        await self.session.commit()
        return draft

    async def submit_for_review(self, draft_id: UUID) -> StrategyProfileDraft:
        draft = await self.get_draft(draft_id)
        if draft.status not in {
            StrategyProfileDraftStatus.DRAFT.value,
            StrategyProfileDraftStatus.REJECTED.value,
        }:
            raise AppError(
                409,
                "strategy_profile_draft_cannot_submit",
                "Only draft or rejected profile drafts can be submitted for review",
            )
        await self.refresh_validation_and_diff(draft)
        if draft.validation_status == StrategyProfileDraftValidationStatus.INVALID.value:
            raise AppError(
                422,
                "strategy_profile_draft_invalid",
                "Strategy profile draft must pass validation before review",
            )
        draft.status = StrategyProfileDraftStatus.READY_FOR_REVIEW.value
        await self.repository.update_draft(draft)
        await self.add_draft_event(
            draft=draft,
            event_type=StrategyProfileDraftEventType.SUBMITTED_FOR_REVIEW,
            user_id=None,
            message="Strategy profile draft submitted for review",
            metadata_json={"validationStatus": draft.validation_status},
        )
        await self.session.commit()
        return draft

    async def approve_draft(
        self,
        draft_id: UUID,
        payload: StrategyProfileDraftWorkflowRequest,
    ) -> StrategyProfileDraft:
        draft = await self.get_draft(draft_id)
        if draft.status != StrategyProfileDraftStatus.READY_FOR_REVIEW.value:
            raise AppError(
                409,
                "strategy_profile_draft_cannot_approve",
                "Only ready-for-review profile drafts can be approved",
            )
        await self.refresh_validation_and_diff(draft)
        if draft.validation_status == StrategyProfileDraftValidationStatus.INVALID.value:
            raise AppError(
                422,
                "strategy_profile_draft_invalid",
                "Invalid profile drafts cannot be approved",
            )
        now = utc_now()
        draft.status = StrategyProfileDraftStatus.APPROVED.value
        draft.reviewed_by_user_id = payload.user_id
        draft.approved_by_user_id = payload.user_id
        draft.review_notes = payload.review_notes
        draft.reviewed_at = now
        draft.approved_at = now
        await self.repository.update_draft(draft)
        await self.add_draft_event(
            draft=draft,
            event_type=StrategyProfileDraftEventType.APPROVED,
            user_id=payload.user_id,
            message="Strategy profile draft approved",
            metadata_json={"validationStatus": draft.validation_status},
        )
        await self.session.commit()
        return draft

    async def reject_draft(
        self,
        draft_id: UUID,
        payload: StrategyProfileDraftWorkflowRequest,
    ) -> StrategyProfileDraft:
        draft = await self.get_draft(draft_id)
        if draft.status not in {
            StrategyProfileDraftStatus.READY_FOR_REVIEW.value,
            StrategyProfileDraftStatus.APPROVED.value,
        }:
            raise AppError(
                409,
                "strategy_profile_draft_cannot_reject",
                "Only reviewed or approved profile drafts can be rejected",
            )
        now = utc_now()
        draft.status = StrategyProfileDraftStatus.REJECTED.value
        draft.reviewed_by_user_id = payload.user_id
        draft.rejected_by_user_id = payload.user_id
        draft.review_notes = payload.review_notes
        draft.reviewed_at = now
        draft.rejected_at = now
        await self.repository.update_draft(draft)
        await self.add_draft_event(
            draft=draft,
            event_type=StrategyProfileDraftEventType.REJECTED,
            user_id=payload.user_id,
            message="Strategy profile draft rejected",
            metadata_json={},
        )
        await self.session.commit()
        return draft

    async def promote_draft(
        self,
        draft_id: UUID,
        payload: StrategyProfileDraftPromotionRequest,
    ) -> StrategyProfileDraft:
        draft = await self.get_draft(draft_id)
        if draft.status != StrategyProfileDraftStatus.APPROVED.value:
            raise AppError(
                409,
                "strategy_profile_draft_cannot_promote",
                "Only approved profile drafts can be promoted",
            )
        await self.refresh_validation_and_diff(draft)
        if draft.validation_status == StrategyProfileDraftValidationStatus.INVALID.value:
            raise AppError(
                422,
                "strategy_profile_draft_invalid",
                "Invalid profile drafts cannot be promoted",
            )
        existing_profile = await self.repository.get_strategy_profile_by_key_version(
            draft.draft_key,
            draft.draft_version,
        )
        if existing_profile is not None:
            raise AppError(
                409,
                "strategy_profile_version_exists",
                "A strategy profile with this key and version already exists",
            )
        profile = await self.repository.create_strategy_profile(
            StrategyProfile(
                key=draft.draft_key,
                name=draft.name,
                description=draft.description,
                version=draft.draft_version,
                is_active=True,
                allowed_patterns_json=list(
                    config_list(draft.proposed_config_json, "allowed_patterns_json")
                ),
                excluded_patterns_json=list(
                    config_list(draft.proposed_config_json, "excluded_patterns_json")
                ),
                minimum_candidate_strength=config_decimal(
                    draft.proposed_config_json,
                    "minimum_candidate_strength",
                ),
                minimum_confidence=config_decimal(draft.proposed_config_json, "minimum_confidence"),
                component_weights_json=config_object(
                    draft.proposed_config_json,
                    "component_weights_json",
                ),
                risk_filters_json=config_object(draft.proposed_config_json, "risk_filters_json"),
                no_signal_rules_json=config_object(
                    draft.proposed_config_json,
                    "no_signal_rules_json",
                ),
            )
        )
        deactivated_profile_ids: list[str] = []
        if payload.deactivate_previous:
            active_profiles = await self.repository.list_active_strategy_profiles_by_key(
                draft.draft_key
            )
            for active_profile in active_profiles:
                if active_profile.id == profile.id:
                    continue
                active_profile.is_active = False
                deactivated_profile_ids.append(str(active_profile.id))
        now = utc_now()
        draft.status = StrategyProfileDraftStatus.PROMOTED.value
        draft.promoted_strategy_profile_id = profile.id
        draft.review_notes = payload.review_notes or draft.review_notes
        draft.promoted_at = now
        await self.repository.update_draft(draft)
        await self.add_draft_event(
            draft=draft,
            event_type=StrategyProfileDraftEventType.PROMOTED,
            user_id=payload.user_id,
            message="Strategy profile draft promoted to active strategy profile version",
            metadata_json={
                "promotedStrategyProfileId": str(profile.id),
                "deactivatePrevious": payload.deactivate_previous,
                "deactivatedStrategyProfileIds": deactivated_profile_ids,
                "validationStatus": draft.validation_status,
                "diff": draft.diff_json,
            },
        )
        await self.session.commit()
        return draft

    async def archive_draft(self, draft_id: UUID) -> StrategyProfileDraft:
        draft = await self.get_draft(draft_id)
        if draft.status == StrategyProfileDraftStatus.PROMOTED.value:
            raise AppError(
                409,
                "strategy_profile_draft_cannot_archive",
                "Promoted profile drafts remain auditable and cannot be archived",
            )
        draft.status = StrategyProfileDraftStatus.ARCHIVED.value
        await self.repository.update_draft(draft)
        await self.add_draft_event(
            draft=draft,
            event_type=StrategyProfileDraftEventType.ARCHIVED,
            user_id=None,
            message="Strategy profile draft archived",
            metadata_json={},
        )
        await self.session.commit()
        return draft

    async def list_events(self, draft_id: UUID) -> list[StrategyProfileDraftEvent]:
        await self.get_draft(draft_id)
        return await self.repository.list_events(draft_id)

    async def add_draft_event(
        self,
        draft: StrategyProfileDraft,
        event_type: StrategyProfileDraftEventType,
        user_id: UUID | None,
        message: str,
        metadata_json: dict[str, object],
    ) -> StrategyProfileDraftEvent:
        return await self.repository.create_event(
            StrategyProfileDraftEvent(
                workspace_id=draft.workspace_id,
                draft_id=draft.id,
                event_type=event_type.value,
                user_id=user_id,
                message=message,
                metadata_json=metadata_json,
            )
        )

    async def refresh_validation_and_diff(self, draft: StrategyProfileDraft) -> None:
        validation = validate_profile_config(
            draft_key=draft.draft_key,
            draft_version=draft.draft_version,
            config=draft.proposed_config_json,
        )
        draft.validation_status = validation.status
        draft.validation_errors_json = validation.errors_json()
        draft.validation_warnings_json = validation.warnings_json()
        await self.refresh_diff(draft)

    async def refresh_diff(self, draft: StrategyProfileDraft) -> None:
        base_profile = await self.resolve_base_profile(
            base_strategy_profile_id=draft.base_strategy_profile_id,
            base_strategy_profile_key=draft.base_strategy_profile_key,
            base_strategy_profile_version=draft.base_strategy_profile_version,
        )
        draft.diff_json = diff_profile_config(
            strategy_profile_config(base_profile),
            draft.proposed_config_json,
        )

    async def resolve_base_profile(
        self,
        base_strategy_profile_id: UUID | None,
        base_strategy_profile_key: str,
        base_strategy_profile_version: str | None,
    ) -> StrategyProfile | None:
        if base_strategy_profile_id is not None:
            profile = await self.repository.get_strategy_profile(base_strategy_profile_id)
            if profile is None:
                raise AppError(
                    404, "base_strategy_profile_not_found", "Base strategy profile not found"
                )
            return profile
        if base_strategy_profile_version is not None:
            return await self.repository.get_strategy_profile_by_key_version(
                base_strategy_profile_key,
                base_strategy_profile_version,
            )
        return await self.repository.get_latest_strategy_profile_by_key(
            base_strategy_profile_key,
            active_only=True,
        )


def config_list(config: dict[str, object], field: str) -> list[str]:
    value = config.get(field)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AppError(422, "invalid_strategy_profile_config", f"{field} must be a list of strings")
    return [str(item) for item in value]


def config_object(config: dict[str, object], field: str) -> dict[str, object]:
    value = config.get(field)
    if not isinstance(value, dict):
        raise AppError(422, "invalid_strategy_profile_config", f"{field} must be an object")
    return value


def config_decimal(config: dict[str, object], field: str) -> Decimal:
    value = config.get(field)
    if value is None:
        raise AppError(422, "invalid_strategy_profile_config", f"{field} is required")
    return Decimal(str(value))


def utc_now() -> datetime:
    return datetime.now(UTC)
