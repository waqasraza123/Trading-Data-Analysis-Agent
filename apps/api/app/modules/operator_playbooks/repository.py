from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operator_playbooks.models import OperatorPlaybook, OperatorPlaybookEvaluation


class OperatorPlaybookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_playbooks(self, enabled_only: bool = False) -> list[OperatorPlaybook]:
        statement: Select[tuple[OperatorPlaybook]] = select(OperatorPlaybook).order_by(
            OperatorPlaybook.priority.asc(),
            OperatorPlaybook.key.asc(),
        )
        if enabled_only:
            statement = statement.where(OperatorPlaybook.is_enabled.is_(True))
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_key(self, key: str) -> OperatorPlaybook | None:
        statement: Select[tuple[OperatorPlaybook]] = (
            select(OperatorPlaybook)
            .where(OperatorPlaybook.key == key)
            .order_by(OperatorPlaybook.version.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_key_version(self, key: str, version: str) -> OperatorPlaybook | None:
        statement = select(OperatorPlaybook).where(
            OperatorPlaybook.key == key,
            OperatorPlaybook.version == version,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_playbook(self, playbook: OperatorPlaybook) -> OperatorPlaybook:
        self.session.add(playbook)
        await self.session.flush()
        await self.session.refresh(playbook)
        return playbook

    async def create_evaluation(
        self,
        evaluation: OperatorPlaybookEvaluation,
    ) -> OperatorPlaybookEvaluation:
        self.session.add(evaluation)
        await self.session.flush()
        await self.session.refresh(evaluation)
        return evaluation

    async def list_evaluations(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
    ) -> list[OperatorPlaybookEvaluation]:
        statement: Select[tuple[OperatorPlaybookEvaluation]] = (
            select(OperatorPlaybookEvaluation)
            .where(OperatorPlaybookEvaluation.workspace_id == workspace_id)
            .order_by(OperatorPlaybookEvaluation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
