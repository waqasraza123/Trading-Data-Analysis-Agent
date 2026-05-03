from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.analysis.models import AnalysisRun
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.outcomes.models import SignalOutcome
from app.modules.setup_context.models import SetupContext
from app.modules.signals.models import Signal
from app.modules.trading_journal.models import (
    JournalEntry,
    JournalEntryAttachment,
    JournalEntryReview,
    JournalEntryStatus,
)
from app.modules.trading_journal.reflection import build_journal_reflection
from app.modules.trading_journal.repository import TradingJournalRepository
from app.modules.trading_journal.schemas import (
    JournalEntryAttachmentCreateRequest,
    JournalEntryAttachmentRead,
    JournalEntryCreateRequest,
    JournalEntryRead,
    JournalEntryReviewRead,
    JournalEntryUpdateRequest,
)
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace


class TradingJournalService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = TradingJournalRepository(session)

    async def create_journal_entry(self, payload: JournalEntryCreateRequest) -> JournalEntryRead:
        await self.ensure_workspace(payload.workspace_id)
        await self.validate_user(payload.workspace_id, payload.user_id)
        signal = await self.validate_signal(payload.workspace_id, payload.signal_id)
        analysis_run_id = payload.analysis_run_id
        if signal is not None:
            analysis_run_id = analysis_run_id or signal.analysis_run_id
        await self.validate_analysis_run(payload.workspace_id, analysis_run_id)
        self.validate_signal_analysis_pair(signal, analysis_run_id)
        await self.validate_chart_screenshot_run(
            payload.workspace_id,
            payload.chart_screenshot_run_id,
        )
        await self.validate_setup_context(payload.workspace_id, payload.setup_context_id)
        entry = await self.repository.create_entry(
            JournalEntry(
                workspace_id=payload.workspace_id,
                user_id=payload.user_id,
                signal_id=payload.signal_id,
                analysis_run_id=analysis_run_id,
                setup_context_id=payload.setup_context_id,
                chart_screenshot_run_id=payload.chart_screenshot_run_id,
                title=payload.title,
                status=payload.status.value,
                decision_type=payload.decision_type.value,
                confidence_before=payload.confidence_before,
                user_bias=payload.user_bias.value if payload.user_bias is not None else None,
                user_notes=payload.user_notes,
                tags_json=normalize_tags(payload.tags),
                metadata_json=payload.metadata,
            )
        )
        await self.session.commit()
        await self.session.refresh(entry)
        return entry_to_read(entry)

    async def get_journal_entry(self, entry_id: UUID) -> JournalEntryRead:
        entry = await self.get_entry_or_raise(entry_id)
        return entry_to_read(entry)

    async def list_journal_entries(
        self,
        workspace_id: UUID,
        user_id: UUID | None = None,
        signal_id: UUID | None = None,
        analysis_run_id: UUID | None = None,
        decision_type: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JournalEntryRead]:
        await self.ensure_workspace(workspace_id)
        entries = await self.repository.list_entries(
            workspace_id=workspace_id,
            user_id=user_id,
            signal_id=signal_id,
            analysis_run_id=analysis_run_id,
            decision_type=decision_type,
            status=status,
            limit=limit,
            offset=offset,
        )
        return [entry_to_read(entry) for entry in entries]

    async def update_journal_entry(
        self,
        entry_id: UUID,
        payload: JournalEntryUpdateRequest,
    ) -> JournalEntryRead:
        entry = await self.get_entry_or_raise(entry_id)
        fields = payload.model_fields_set
        if "user_id" in fields:
            await self.validate_user(entry.workspace_id, payload.user_id)
            entry.user_id = payload.user_id
        if "signal_id" in fields:
            signal = await self.validate_signal(entry.workspace_id, payload.signal_id)
            entry.signal_id = payload.signal_id
            if signal is not None and entry.analysis_run_id is None:
                entry.analysis_run_id = signal.analysis_run_id
        else:
            signal = await self.validate_signal(entry.workspace_id, entry.signal_id)
        if "analysis_run_id" in fields:
            await self.validate_analysis_run(entry.workspace_id, payload.analysis_run_id)
            entry.analysis_run_id = payload.analysis_run_id
        self.validate_signal_analysis_pair(signal, entry.analysis_run_id)
        if "chart_screenshot_run_id" in fields:
            await self.validate_chart_screenshot_run(
                entry.workspace_id,
                payload.chart_screenshot_run_id,
            )
            entry.chart_screenshot_run_id = payload.chart_screenshot_run_id
        if "setup_context_id" in fields:
            await self.validate_setup_context(entry.workspace_id, payload.setup_context_id)
            entry.setup_context_id = payload.setup_context_id
        if payload.title is not None:
            entry.title = payload.title
        if payload.status is not None:
            entry.status = payload.status.value
        if payload.decision_type is not None:
            entry.decision_type = payload.decision_type.value
        if "confidence_before" in fields:
            entry.confidence_before = payload.confidence_before
        if "user_bias" in fields:
            entry.user_bias = payload.user_bias.value if payload.user_bias is not None else None
        if payload.user_notes is not None:
            entry.user_notes = payload.user_notes
        if payload.tags is not None:
            entry.tags_json = normalize_tags(payload.tags)
        if payload.metadata is not None:
            entry.metadata_json = payload.metadata
        await self.repository.update_entry(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry_to_read(entry)

    async def archive_journal_entry(self, entry_id: UUID) -> JournalEntryRead:
        entry = await self.get_entry_or_raise(entry_id)
        entry.status = JournalEntryStatus.ARCHIVED.value
        await self.repository.update_entry(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry_to_read(entry)

    async def attach_reference(
        self,
        entry_id: UUID,
        payload: JournalEntryAttachmentCreateRequest,
    ) -> JournalEntryAttachmentRead:
        entry = await self.get_entry_or_raise(entry_id)
        await self.validate_reference_workspace(
            workspace_id=entry.workspace_id,
            reference_type=payload.reference_type,
            reference_id=payload.reference_id,
        )
        attachment = await self.repository.create_attachment(
            JournalEntryAttachment(
                workspace_id=entry.workspace_id,
                journal_entry_id=entry.id,
                attachment_type=payload.attachment_type.value,
                reference_type=payload.reference_type,
                reference_id=payload.reference_id,
                metadata_json=payload.metadata,
            )
        )
        await self.session.commit()
        await self.session.refresh(attachment)
        return attachment_to_read(attachment)

    async def review_journal_entry_against_outcome(
        self,
        entry_id: UUID,
        outcome_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> JournalEntryReviewRead:
        entry = await self.get_entry_or_raise(entry_id)
        outcome = await self.resolve_review_outcome(entry, outcome_id)
        result = build_journal_reflection(
            decision_type=entry.decision_type,
            user_bias=entry.user_bias,
            outcome=outcome,
        )
        review_metadata = {
            **result.metadata,
            **(metadata or {}),
            "deterministicTemplate": True,
            "journalReviewVersion": self.settings.journal_review_version,
            "llmUsed": False,
            "mutatedSignal": False,
            "mutatedOutcome": False,
        }
        review = await self.repository.create_review(
            JournalEntryReview(
                workspace_id=entry.workspace_id,
                journal_entry_id=entry.id,
                reviewed_at=utc_now(),
                outcome_id=outcome.id if outcome is not None else None,
                outcome_label=outcome.outcome_label if outcome is not None else None,
                reflection_label=result.reflection_label.value,
                reflection_notes=result.reflection_notes,
                lessons_json=result.lessons,
                metadata_json=review_metadata,
            )
        )
        await self.session.commit()
        await self.session.refresh(review)
        return review_to_read(review)

    async def list_journal_reviews(self, entry_id: UUID) -> list[JournalEntryReviewRead]:
        await self.get_entry_or_raise(entry_id)
        reviews = await self.repository.list_reviews(entry_id)
        return [review_to_read(review) for review in reviews]

    async def get_entry_or_raise(self, entry_id: UUID) -> JournalEntry:
        entry = await self.repository.get_entry(entry_id)
        if entry is None:
            raise AppError(404, "journal_entry_not_found", "Journal entry not found")
        return entry

    async def ensure_workspace(self, workspace_id: UUID) -> None:
        workspace = await self.session.get(Workspace, workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")

    async def validate_user(self, workspace_id: UUID, user_id: UUID | None) -> None:
        if user_id is None:
            return
        user = await self.session.get(User, user_id)
        if user is None:
            raise AppError(404, "user_not_found", "User not found")
        if user.workspace_id != workspace_id:
            raise AppError(422, "workspace_mismatch", "User belongs to a different workspace")

    async def validate_signal(self, workspace_id: UUID, signal_id: UUID | None) -> Signal | None:
        if signal_id is None:
            return None
        signal = await self.session.get(Signal, signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        if signal.workspace_id != workspace_id:
            raise AppError(422, "workspace_mismatch", "Signal belongs to a different workspace")
        return signal

    async def validate_analysis_run(
        self,
        workspace_id: UUID,
        analysis_run_id: UUID | None,
    ) -> None:
        if analysis_run_id is None:
            return
        analysis_run = await self.session.get(AnalysisRun, analysis_run_id)
        if analysis_run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        if analysis_run.workspace_id != workspace_id:
            raise AppError(
                422,
                "workspace_mismatch",
                "Analysis run belongs to a different workspace",
            )

    async def validate_chart_screenshot_run(
        self,
        workspace_id: UUID,
        chart_screenshot_run_id: UUID | None,
    ) -> None:
        if chart_screenshot_run_id is None:
            return
        run = await self.session.get(ChartScreenshotRun, chart_screenshot_run_id)
        if run is None:
            raise AppError(404, "chart_screenshot_run_not_found", "Chart screenshot run not found")
        if run.workspace_id != workspace_id:
            raise AppError(
                422,
                "workspace_mismatch",
                "Chart screenshot run belongs to a different workspace",
            )

    async def validate_reference_workspace(
        self,
        workspace_id: UUID,
        reference_type: str,
        reference_id: UUID,
    ) -> None:
        model_by_reference_type: dict[str, type[Any]] = {
            "analysis_run": AnalysisRun,
            "chart_screenshot_run": ChartScreenshotRun,
            "outcome": SignalOutcome,
            "setup_context": SetupContext,
            "signal": Signal,
            "user": User,
        }
        model = model_by_reference_type.get(reference_type)
        if model is None:
            return
        reference = await self.session.get(model, reference_id)
        if reference is None:
            raise AppError(404, "reference_not_found", "Attachment reference not found")
        if getattr(reference, "workspace_id", None) != workspace_id:
            raise AppError(
                422,
                "workspace_mismatch",
                "Attachment reference belongs to a different workspace",
            )

    async def resolve_review_outcome(
        self,
        entry: JournalEntry,
        outcome_id: UUID | None,
    ) -> SignalOutcome | None:
        if outcome_id is None:
            if entry.signal_id is None:
                return None
            return await self.repository.get_latest_outcome_for_signal(entry.signal_id)
        outcome = await self.repository.get_outcome(outcome_id)
        if outcome is None:
            raise AppError(404, "outcome_not_found", "Signal outcome not found")
        if outcome.workspace_id != entry.workspace_id:
            raise AppError(422, "workspace_mismatch", "Outcome belongs to a different workspace")
        if entry.signal_id is not None and outcome.signal_id != entry.signal_id:
            raise AppError(
                422,
                "outcome_signal_mismatch",
                "Outcome does not belong to the journal entry signal",
            )
        return outcome

    def validate_signal_analysis_pair(
        self,
        signal: Signal | None,
        analysis_run_id: UUID | None,
    ) -> None:
        if (
            signal is not None
            and analysis_run_id is not None
            and signal.analysis_run_id != analysis_run_id
        ):
            raise AppError(
                422,
                "signal_analysis_run_mismatch",
                "Signal does not belong to the analysis run",
            )

    async def validate_setup_context(
        self,
        workspace_id: UUID,
        setup_context_id: UUID | None,
    ) -> None:
        if setup_context_id is None:
            return
        setup_context = await self.session.get(SetupContext, setup_context_id)
        if setup_context is None:
            raise AppError(404, "setup_context_not_found", "Setup context not found")
        if setup_context.workspace_id != workspace_id:
            raise AppError(
                422,
                "workspace_mismatch",
                "Setup context belongs to a different workspace",
            )


def normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        value = " ".join(tag.strip().split())
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(value[:80])
    return normalized


def entry_to_read(entry: JournalEntry) -> JournalEntryRead:
    return JournalEntryRead(
        id=entry.id,
        workspace_id=entry.workspace_id,
        user_id=entry.user_id,
        signal_id=entry.signal_id,
        analysis_run_id=entry.analysis_run_id,
        setup_context_id=entry.setup_context_id,
        chart_screenshot_run_id=entry.chart_screenshot_run_id,
        title=entry.title,
        status=entry.status,
        decision_type=entry.decision_type,
        confidence_before=entry.confidence_before,
        user_bias=entry.user_bias,
        user_notes=entry.user_notes,
        tags=list(entry.tags_json or []),
        metadata=dict(entry.metadata_json or {}),
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def review_to_read(review: JournalEntryReview) -> JournalEntryReviewRead:
    return JournalEntryReviewRead(
        id=review.id,
        workspace_id=review.workspace_id,
        journal_entry_id=review.journal_entry_id,
        reviewed_at=review.reviewed_at,
        outcome_id=review.outcome_id,
        outcome_label=review.outcome_label,
        reflection_label=review.reflection_label,
        reflection_notes=review.reflection_notes,
        lessons=list(review.lessons_json or []),
        metadata=dict(review.metadata_json or {}),
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def attachment_to_read(attachment: JournalEntryAttachment) -> JournalEntryAttachmentRead:
    return JournalEntryAttachmentRead(
        id=attachment.id,
        workspace_id=attachment.workspace_id,
        journal_entry_id=attachment.journal_entry_id,
        attachment_type=attachment.attachment_type,
        reference_type=attachment.reference_type,
        reference_id=attachment.reference_id,
        metadata=dict(attachment.metadata_json or {}),
        created_at=attachment.created_at,
    )
