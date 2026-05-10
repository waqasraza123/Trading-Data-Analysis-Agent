from __future__ import annotations

from typing import Any

from .evaluator import SafetyPolicy, SafetyPolicyEvaluator, default_policy
from .redaction import redact_payload as redact_payload_shape
from .repository import SafetyPolicyRepository
from .schemas import (
    SafetyEvaluationResponse,
    SafetyPolicyEvaluationType,
    SafetyPolicyRules,
    SafetyPolicySetData,
    SafetyPolicySetStatus,
)

DEFAULT_POLICY_DESCRIPTION = (
    "Core safety policy for market intelligence, non-execution analysis, "
    "public payload redaction, and operator-safe recommendations."
)


class SafetyPolicyService:
    def __init__(
        self,
        repository: SafetyPolicyRepository | None = None,
        evaluator: SafetyPolicyEvaluator | None = None,
    ) -> None:
        self.repository = repository
        self.evaluator = evaluator or SafetyPolicyEvaluator()

    async def seed_default_policy_set(self, workspace_id: str | None = None) -> SafetyPolicySetData:
        active_policy = default_policy()
        policy_data = SafetyPolicySetData(
            key=active_policy.key,
            version=active_policy.version,
            status=SafetyPolicySetStatus.ACTIVE,
            description=DEFAULT_POLICY_DESCRIPTION,
            rules=active_policy.rules,
        )
        if self.repository is not None:
            await self.repository.upsert_policy_set(
                key=policy_data.key,
                version=policy_data.version,
                status=policy_data.status,
                description=policy_data.description,
                policy_json=policy_data.model_dump(mode="json", by_alias=True),
                workspace_id=workspace_id,
            )
        return policy_data

    async def get_active_policy_set(
        self, workspace_id: str | None = None, key: str = "core_market_intelligence"
    ) -> SafetyPolicy:
        if self.repository is None:
            return default_policy()
        policy_set = await self.repository.get_policy_set(
            key=key,
            workspace_id=workspace_id,
            status=SafetyPolicySetStatus.ACTIVE,
        )
        if policy_set is None:
            return default_policy()
        policy_json = policy_set.policy_json or {}
        rules_data = policy_json.get("rules", policy_json)
        return SafetyPolicy(
            key=policy_set.key,
            version=policy_set.version,
            rules=SafetyPolicyRules.model_validate(rules_data),
        )

    async def evaluate_text(
        self,
        text: str,
        workspace_id: str | None = None,
        source_type: str = "manual",
        source_id: str | None = None,
    ) -> SafetyEvaluationResponse:
        policy = await self.get_active_policy_set(workspace_id)
        result = self.evaluator.evaluate_text(text, policy)
        await self._persist_result(workspace_id, source_type, source_id, result)
        return result

    async def evaluate_action(
        self,
        action: str,
        workspace_id: str | None = None,
        source_type: str = "manual",
        source_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> SafetyEvaluationResponse:
        policy = await self.get_active_policy_set(workspace_id)
        result = self.evaluator.evaluate_action(action, policy, context)
        await self._persist_result(workspace_id, source_type, source_id, result)
        return result

    async def evaluate_payload(
        self,
        payload: dict[str, Any],
        workspace_id: str | None = None,
        source_type: str = "manual",
        source_id: str | None = None,
        public_response: bool = True,
    ) -> SafetyEvaluationResponse:
        policy = await self.get_active_policy_set(workspace_id)
        result = self.evaluator.evaluate_payload(
            payload, policy, SafetyPolicyEvaluationType.PAYLOAD, public_response
        )
        await self._persist_result(workspace_id, source_type, source_id, result)
        return result

    async def evaluate_report(
        self,
        report: str,
        workspace_id: str | None = None,
        source_type: str = "report",
        source_id: str | None = None,
    ) -> SafetyEvaluationResponse:
        policy = await self.get_active_policy_set(workspace_id)
        result = self.evaluator.evaluate_report(report, policy)
        await self._persist_result(workspace_id, source_type, source_id, result)
        return result

    async def evaluate_webhook_payload(
        self,
        payload: dict[str, Any],
        workspace_id: str | None = None,
        source_type: str = "webhook",
        source_id: str | None = None,
    ) -> SafetyEvaluationResponse:
        policy = await self.get_active_policy_set(workspace_id)
        result = self.evaluator.evaluate_webhook_payload(payload, policy)
        await self._persist_result(workspace_id, source_type, source_id, result)
        return result

    async def evaluate_reasoning_output(
        self,
        output: str,
        workspace_id: str | None = None,
        source_type: str = "reasoning",
        source_id: str | None = None,
    ) -> SafetyEvaluationResponse:
        policy = await self.get_active_policy_set(workspace_id)
        result = self.evaluator.evaluate_reasoning_output(output, policy)
        await self._persist_result(workspace_id, source_type, source_id, result)
        return result

    async def evaluate_dataset_record(
        self,
        payload: dict[str, Any],
        workspace_id: str | None = None,
        source_type: str = "dataset",
        source_id: str | None = None,
    ) -> SafetyEvaluationResponse:
        policy = await self.get_active_policy_set(workspace_id)
        result = self.evaluator.evaluate_dataset_record(payload, policy)
        await self._persist_result(workspace_id, source_type, source_id, result)
        return result

    async def redact_payload(self, payload: object, workspace_id: str | None = None) -> object:
        policy = await self.get_active_policy_set(workspace_id)
        return redact_payload_shape(payload, policy.rules.secret_keys)

    async def _persist_result(
        self,
        workspace_id: str | None,
        source_type: str,
        source_id: str | None,
        result: SafetyEvaluationResponse,
    ) -> None:
        if self.repository is None:
            return
        await self.repository.create_evaluation(
            workspace_id=workspace_id,
            source_type=source_type,
            source_id=source_id,
            result=result,
        )
