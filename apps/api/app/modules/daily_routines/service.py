from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.daily_routines.models import (
    DailyRoutineRun,
    DailyRoutineRunStatus,
    DailyRoutineRunStep,
    DailyRoutineTemplate,
    DailyRoutineTemplateStatus,
)
from app.modules.daily_routines.repository import DailyRoutineRepository
from app.modules.daily_routines.runner import DailyRoutineRunner, parse_step_definitions
from app.modules.daily_routines.schemas import (
    DailyRoutineRunListFilters,
    DailyRoutineRunRequest,
    DailyRoutineTemplateListFilters,
)
from app.modules.daily_routines.seed import default_daily_routine_templates


class DailyRoutineService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        repository: DailyRoutineRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or DailyRoutineRepository(session)

    async def seed_default_routine_templates(self) -> list[DailyRoutineTemplate]:
        seeded: list[DailyRoutineTemplate] = []
        for definition in default_daily_routine_templates(self.settings.daily_routine_version):
            existing = await self.repository.get_template_by_key_version(
                definition.key,
                definition.routine_version,
                workspace_id=None,
            )
            if existing is None:
                seeded.append(await self.repository.create_template(definition))
                continue
            update_template(existing, definition)
            seeded.append(existing)
        await self.session.commit()
        return seeded

    async def list_routine_templates(
        self,
        filters: DailyRoutineTemplateListFilters,
    ) -> list[DailyRoutineTemplate]:
        return await self.repository.list_templates(
            workspace_id=filters.workspace_id,
            routine_type=filters.routine_type.value if filters.routine_type is not None else None,
            status=filters.status.value if filters.status is not None else None,
        )

    async def get_routine_template(
        self,
        template_id: UUID,
        workspace_id: UUID | None = None,
    ) -> DailyRoutineTemplate:
        template = await self.repository.get_template(template_id)
        if template is None:
            raise AppError(404, "daily_routine_template_not_found", "Routine template not found")
        if template.status == DailyRoutineTemplateStatus.ARCHIVED.value:
            raise AppError(404, "daily_routine_template_not_found", "Routine template not found")
        if (
            template.workspace_id is not None
            and workspace_id is not None
            and template.workspace_id != workspace_id
        ):
            raise AppError(
                422,
                "workspace_template_mismatch",
                "Routine template does not belong to workspace",
            )
        return template

    async def run_routine(
        self,
        template_id: UUID,
        payload: DailyRoutineRunRequest,
    ) -> DailyRoutineRun:
        await self.validate_workspace(payload.workspace_id)
        template = await self.get_routine_template(template_id, workspace_id=payload.workspace_id)
        definitions = parse_step_definitions(template.steps_json)
        if not definitions:
            raise AppError(422, "daily_routine_empty_template", "Routine template has no steps")
        if len(definitions) > self.settings.daily_routine_max_steps:
            raise AppError(
                422,
                "daily_routine_too_many_steps",
                "Routine template exceeds the configured maximum step count",
            )
        existing = await self.repository.get_active_run(
            workspace_id=payload.workspace_id,
            template_id=template.id,
        )
        if existing is not None:
            return existing
        input_json = build_run_input(template, payload)
        run = DailyRoutineRun(
            workspace_id=payload.workspace_id,
            template_id=template.id,
            status=DailyRoutineRunStatus.PENDING.value,
            routine_version=template.routine_version,
            input_json=input_json,
            step_results_json=[],
            created_artifact_ids_json={},
            summary="Daily routine pending",
            error_message=None,
            started_at=utc_now(),
        )
        try:
            created = await self.repository.create_run(run)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "daily_routine_run_conflict",
                "Routine run could not be persisted",
            ) from error
        return await DailyRoutineRunner(
            self.session,
            settings=self.settings,
            repository=self.repository,
        ).run(created, template, payload)

    async def get_routine_run(self, run_id: UUID) -> DailyRoutineRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(404, "daily_routine_run_not_found", "Routine run not found")
        return run

    async def list_routine_runs(self, filters: DailyRoutineRunListFilters) -> list[DailyRoutineRun]:
        await self.validate_workspace(filters.workspace_id)
        return await self.repository.list_runs(
            workspace_id=filters.workspace_id,
            template_id=filters.template_id,
            status=filters.status.value if filters.status is not None else None,
            limit=filters.limit,
            offset=filters.offset,
        )

    async def list_routine_run_steps(self, run_id: UUID) -> list[DailyRoutineRunStep]:
        await self.get_routine_run(run_id)
        return await self.repository.list_steps(run_id)

    async def validate_workspace(self, workspace_id: UUID) -> None:
        workspace = await self.repository.get_workspace(workspace_id)
        if workspace is None:
            raise AppError(404, "workspace_not_found", "Workspace not found")


def update_template(target: DailyRoutineTemplate, source: DailyRoutineTemplate) -> None:
    target.name = source.name
    target.description = source.description
    target.status = source.status
    target.routine_type = source.routine_type
    target.steps_json = source.steps_json
    target.default_filters_json = source.default_filters_json
    target.schedule_hint_json = source.schedule_hint_json
    target.metadata_json = source.metadata_json


def build_run_input(
    template: DailyRoutineTemplate,
    payload: DailyRoutineRunRequest,
) -> dict[str, object]:
    return {
        "templateKey": template.key,
        "routineType": template.routine_type,
        "defaultFilters": template.default_filters_json,
        "request": payload.model_dump(mode="json", by_alias=True),
        "safety": {
            "noBrokerExecution": True,
            "noAutoTrading": True,
            "noFinancialAdvice": True,
            "externalNotificationsEnabled": bool(payload.enable_notifications),
        },
    }
