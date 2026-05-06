from typing import Any, cast
from uuid import uuid4

import pytest

from app.config import Settings
from app.core.errors import AppError
from app.modules.workspace_actions.schemas import WorkspaceQuickActionRequest
from app.modules.workspace_actions.service import WorkspaceQuickActionService, normalize_action_type


class FakeWorkspaceRepository:
    async def get_by_id(self, workspace_id: object) -> object:
        return object()


def make_service() -> WorkspaceQuickActionService:
    service = WorkspaceQuickActionService(cast(Any, object()), settings=Settings(_env_file=None))
    service.workspace_repository = cast(Any, FakeWorkspaceRepository())
    return service


def test_normalize_action_type_accepts_human_variants() -> None:
    assert normalize_action_type("Run Daily Workflow") == "run_daily_workflow"
    assert normalize_action_type("refresh-provider-health") == "refresh_provider_health"


@pytest.mark.asyncio
async def test_quick_action_rejects_unsafe_action() -> None:
    service = make_service()

    with pytest.raises(AppError) as error:
        await service.run_action(uuid4(), WorkspaceQuickActionRequest(action_type="place_order"))

    assert error.value.status_code == 400
    assert error.value.code == "unsafe_action_rejected"


@pytest.mark.asyncio
async def test_quick_action_returns_unsupported_for_unknown_safe_action() -> None:
    service = make_service()

    with pytest.raises(AppError) as error:
        await service.run_action(
            uuid4(), WorkspaceQuickActionRequest(action_type="refresh_calendar")
        )

    assert error.value.status_code == 400
    assert error.value.code == "unsupported_action"
