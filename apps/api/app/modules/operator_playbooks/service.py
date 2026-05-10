from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.operator_playbooks.models import (
    OperatorPlaybook,
    OperatorPlaybookEvaluation,
    OperatorPlaybookEvaluationStatus,
    OperatorPlaybookRecommendationType,
)
from app.modules.operator_playbooks.repository import OperatorPlaybookRepository
from app.modules.operator_playbooks.schemas import OperatorPlaybookEvaluationRequest


class OperatorPlaybookService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = OperatorPlaybookRepository(session)

    async def list_playbooks(self) -> list[OperatorPlaybook]:
        return await self.repository.list_playbooks()

    async def get_playbook(self, key: str) -> OperatorPlaybook:
        playbook = await self.repository.get_by_key(key)
        if playbook is None:
            raise AppError(404, "operator_playbook_not_found", "Operator playbook not found")
        return playbook

    async def seed_playbooks(self) -> list[OperatorPlaybook]:
        if not self.settings.operator_playbook_seed_enabled:
            return await self.repository.list_playbooks()
        seeded: list[OperatorPlaybook] = []
        for definition in default_playbooks(self.settings.operator_playbook_version):
            existing = await self.repository.get_by_key_version(definition.key, definition.version)
            if existing is not None:
                seeded.append(existing)
                continue
            seeded.append(await self.repository.create_playbook(definition))
        await self.session.commit()
        return seeded

    async def evaluate(
        self,
        request: OperatorPlaybookEvaluationRequest,
    ) -> OperatorPlaybookEvaluation:
        playbooks = await self.repository.list_playbooks(enabled_only=True)
        playbook = playbooks[0] if playbooks else None
        recommendation_type = choose_recommendation(request.input_json)
        evaluation = await self.repository.create_evaluation(
            OperatorPlaybookEvaluation(
                workspace_id=request.workspace_id,
                playbook_id=playbook.id if playbook is not None else None,
                status=OperatorPlaybookEvaluationStatus.COMPLETED.value,
                recommendation_type=recommendation_type.value,
                subject_type=request.subject_type,
                subject_id=request.subject_id,
                rationale=recommendation_rationale(recommendation_type),
                input_json=request.input_json,
                result_json={
                    "operatorRecommendation": recommendation_type.value,
                    "autoApplied": False,
                    "actionExecuted": False,
                },
            )
        )
        await self.session.commit()
        return evaluation

    async def list_evaluations(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
    ) -> list[OperatorPlaybookEvaluation]:
        return await self.repository.list_evaluations(workspace_id, limit, offset)


def default_playbooks(version: str) -> tuple[OperatorPlaybook, ...]:
    return (
        OperatorPlaybook(
            key="calibration_review",
            version=version,
            name="Calibration Review",
            description=(
                "Suggests manual review when diagnostics or simulations indicate changed decisions."
            ),
            is_enabled=True,
            priority=10,
            rules_json={"uses": ["profile_diagnostics", "profile_simulations"]},
        ),
        OperatorPlaybook(
            key="data_quality_review",
            version=version,
            name="Data Quality Review",
            description=(
                "Suggests manual review when data quality findings may affect interpretation."
            ),
            is_enabled=True,
            priority=20,
            rules_json={"uses": ["data_quality", "decision_readiness"]},
        ),
    )


def choose_recommendation(input_json: dict[str, object]) -> OperatorPlaybookRecommendationType:
    if input_json.get("dataQualityLabel") in {"poor", "degraded", "insufficient_data"}:
        return OperatorPlaybookRecommendationType.REVIEW_DATA_QUALITY
    if input_json.get("diagnosticLabel") == "needs_threshold_review":
        return OperatorPlaybookRecommendationType.REVIEW_PROFILE_SIMULATION
    if input_json.get("decisionReadiness") in {"blocked", "warning"}:
        return OperatorPlaybookRecommendationType.REVIEW_DECISION_READINESS
    if input_json.get("marketSessionLabel") in {"overlap", "off_hours"}:
        return OperatorPlaybookRecommendationType.REVIEW_MARKET_SESSION
    return OperatorPlaybookRecommendationType.NO_ACTION


def recommendation_rationale(recommendation_type: OperatorPlaybookRecommendationType) -> str:
    if recommendation_type == OperatorPlaybookRecommendationType.NO_ACTION:
        return "No operator playbook review condition was triggered."
    return "A safe operator recommendation was generated for manual review only."
