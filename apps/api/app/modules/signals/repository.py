from uuid import UUID

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)


class SignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def delete_for_analysis_run(self, analysis_run_id: UUID) -> None:
        await self.session.execute(delete(Signal).where(Signal.analysis_run_id == analysis_run_id))
        await self.session.flush()

    async def create_signal(
        self,
        signal: Signal,
        confidence_components: list[SignalConfidenceComponent],
        evidence: list[SignalEvidence],
        risk_notes: list[SignalRiskNote],
    ) -> Signal:
        self.session.add(signal)
        await self.session.flush()
        await self.session.refresh(signal)
        for component in confidence_components:
            component.signal_id = signal.id
        for evidence_row in evidence:
            evidence_row.signal_id = signal.id
        for risk_note in risk_notes:
            risk_note.signal_id = signal.id
        self.session.add_all(confidence_components)
        self.session.add_all(evidence)
        self.session.add_all(risk_notes)
        await self.session.flush()
        await self.session.refresh(signal)
        return signal

    async def get_by_id(self, signal_id: UUID) -> Signal | None:
        return await self.session.get(Signal, signal_id)

    async def get_by_analysis_run_id(self, analysis_run_id: UUID) -> Signal | None:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .where(Signal.analysis_run_id == analysis_run_id)
            .order_by(Signal.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_confidence_components(
        self,
        signal_id: UUID,
    ) -> list[SignalConfidenceComponent]:
        statement: Select[tuple[SignalConfidenceComponent]] = (
            select(SignalConfidenceComponent)
            .where(SignalConfidenceComponent.signal_id == signal_id)
            .order_by(SignalConfidenceComponent.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_evidence(self, signal_id: UUID) -> list[SignalEvidence]:
        statement: Select[tuple[SignalEvidence]] = (
            select(SignalEvidence)
            .where(SignalEvidence.signal_id == signal_id)
            .order_by(SignalEvidence.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_risk_notes(self, signal_id: UUID) -> list[SignalRiskNote]:
        statement: Select[tuple[SignalRiskNote]] = (
            select(SignalRiskNote)
            .where(SignalRiskNote.signal_id == signal_id)
            .order_by(SignalRiskNote.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
