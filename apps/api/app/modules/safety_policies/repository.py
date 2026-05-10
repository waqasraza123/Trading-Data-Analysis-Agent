from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import SafetyPolicyEvaluation, SafetyPolicySet
from .schemas import SafetyEvaluationResponse, SafetyPolicySetStatus


class SafetyPolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_policy_sets(self, workspace_id: str | None = None) -> list[SafetyPolicySet]:
        statement = select(SafetyPolicySet)
        if workspace_id is not None:
            statement = statement.where(SafetyPolicySet.workspace_id == workspace_id)
        result = await self.session.execute(
            statement.order_by(SafetyPolicySet.key, SafetyPolicySet.version)
        )
        return list(result.scalars().all())

    async def get_policy_set(
        self,
        key: str,
        version: str | None = None,
        workspace_id: str | None = None,
        status: SafetyPolicySetStatus | None = None,
    ) -> SafetyPolicySet | None:
        statement = select(SafetyPolicySet).where(SafetyPolicySet.key == key)
        if version is not None:
            statement = statement.where(SafetyPolicySet.version == version)
        if workspace_id is not None:
            statement = statement.where(SafetyPolicySet.workspace_id == workspace_id)
        if status is not None:
            statement = statement.where(SafetyPolicySet.status == status.value)
        statement = statement.order_by(SafetyPolicySet.created_at.desc())
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def upsert_policy_set(
        self,
        key: str,
        version: str,
        status: SafetyPolicySetStatus,
        description: str,
        policy_json: dict[str, object],
        workspace_id: str | None = None,
    ) -> SafetyPolicySet:
        existing = await self.get_policy_set(key=key, version=version, workspace_id=workspace_id)
        if existing is not None:
            existing.status = status.value
            existing.description = description
            existing.policy_json = policy_json
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        policy_set = SafetyPolicySet(
            workspace_id=workspace_id,
            key=key,
            version=version,
            status=status.value,
            description=description,
            policy_json=policy_json,
        )
        self.session.add(policy_set)
        await self.session.commit()
        await self.session.refresh(policy_set)
        return policy_set

    async def create_evaluation(
        self,
        workspace_id: str | None,
        source_type: str,
        source_id: str | None,
        result: SafetyEvaluationResponse,
    ) -> SafetyPolicyEvaluation:
        evaluation = SafetyPolicyEvaluation(
            workspace_id=workspace_id,
            policy_set_key=result.policy_set_key,
            policy_set_version=result.policy_set_version,
            source_type=source_type,
            source_id=source_id,
            evaluation_type=result.evaluation_type.value,
            status=result.status.value,
            safety_status=result.safety_status.value,
            input_summary_json=result.input_summary_json,
            findings_json=[finding.model_dump(by_alias=True) for finding in result.findings],
            redacted_output_json=result.redacted_output_json,
        )
        self.session.add(evaluation)
        await self.session.commit()
        await self.session.refresh(evaluation)
        return evaluation
