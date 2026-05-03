from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.trading_journal.models import (
    JournalAttachmentType,
    JournalDecisionType,
    JournalEntryStatus,
    JournalReflectionLabel,
    JournalUserBias,
)


class JournalEntryCreateRequest(ApiSchema):
    workspace_id: UUID
    user_id: UUID | None = None
    signal_id: UUID | None = None
    analysis_run_id: UUID | None = None
    setup_context_id: UUID | None = None
    chart_screenshot_run_id: UUID | None = None
    title: str = Field(min_length=1, max_length=240)
    status: JournalEntryStatus = JournalEntryStatus.SAVED
    decision_type: JournalDecisionType
    confidence_before: Decimal | None = Field(default=None, ge=0, le=1)
    user_bias: JournalUserBias | None = None
    user_notes: str = Field(default="", max_length=8000)
    tags: list[str] = Field(default_factory=list, max_length=50)
    metadata: dict[str, Any] = Field(default_factory=dict)


class JournalEntryUpdateRequest(ApiSchema):
    user_id: UUID | None = None
    signal_id: UUID | None = None
    analysis_run_id: UUID | None = None
    setup_context_id: UUID | None = None
    chart_screenshot_run_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    status: JournalEntryStatus | None = None
    decision_type: JournalDecisionType | None = None
    confidence_before: Decimal | None = Field(default=None, ge=0, le=1)
    user_bias: JournalUserBias | None = None
    user_notes: str | None = Field(default=None, max_length=8000)
    tags: list[str] | None = Field(default=None, max_length=50)
    metadata: dict[str, Any] | None = None


class JournalEntryAttachmentCreateRequest(ApiSchema):
    attachment_type: JournalAttachmentType
    reference_type: str = Field(min_length=1, max_length=80)
    reference_id: UUID
    metadata: dict[str, Any] = Field(default_factory=dict)


class JournalEntryReviewCreateRequest(ApiSchema):
    outcome_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class JournalEntryRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    user_id: UUID | None
    signal_id: UUID | None
    analysis_run_id: UUID | None
    setup_context_id: UUID | None
    chart_screenshot_run_id: UUID | None
    title: str
    status: JournalEntryStatus
    decision_type: JournalDecisionType
    confidence_before: Decimal | None
    user_bias: JournalUserBias | None
    user_notes: str
    tags: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class JournalEntryReviewRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    journal_entry_id: UUID
    reviewed_at: datetime
    outcome_id: UUID | None
    outcome_label: str | None
    reflection_label: JournalReflectionLabel
    reflection_notes: str
    lessons: list[str]
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class JournalEntryAttachmentRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    journal_entry_id: UUID
    attachment_type: JournalAttachmentType
    reference_type: str
    reference_id: UUID
    metadata: dict[str, Any]
    created_at: datetime
