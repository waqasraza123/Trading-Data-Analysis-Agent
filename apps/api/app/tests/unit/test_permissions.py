from uuid import uuid4

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from app.config import AppEnvironment, Settings
from app.main import create_app
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.permissions.service import get_permissions_for_role, user_has_permission
from app.modules.users.models import User, UserRole


def test_role_permission_mapping() -> None:
    admin_permissions = get_permissions_for_role(UserRole.ADMIN)
    analyst_permissions = get_permissions_for_role(UserRole.ANALYST)
    user_permissions = get_permissions_for_role(UserRole.USER)

    assert set(admin_permissions) == set(Permission)
    assert Permission.SCANS_WRITE in analyst_permissions
    assert Permission.JOURNAL_WRITE in user_permissions
    assert Permission.CREDENTIALS_ADMIN not in analyst_permissions
    assert Permission.USERS_ADMIN not in user_permissions


def test_user_has_permission_respects_workspace_scope() -> None:
    workspace_id = uuid4()
    other_workspace_id = uuid4()
    user = User(
        id=uuid4(),
        workspace_id=workspace_id,
        email="analyst@example.test",
        name="Analyst",
        role=UserRole.ANALYST.value,
    )

    assert user_has_permission(user, Permission.SCANS_WRITE, workspace_id)
    assert not user_has_permission(user, Permission.SCANS_WRITE, other_workspace_id)
    assert not user_has_permission(user, Permission.USERS_ADMIN, workspace_id)


@pytest.mark.asyncio
async def test_permission_dependency_allows_local_when_auth_disabled() -> None:
    test_app = create_app(Settings(_env_file=None, app_env=AppEnvironment.TEST))

    @test_app.post(
        "/permission-test",
        dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
    )
    async def permission_test() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.post("/permission-test")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_permission_dependency_accepts_admin_api_key_when_auth_enabled() -> None:
    test_app = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TEST,
            auth_enabled=True,
            admin_api_key=SecretStr("correct-key"),
        )
    )

    @test_app.get(
        "/permission-test",
        dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
    )
    async def permission_test() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/permission-test",
            headers={"x-admin-api-key": "correct-key"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_permission_dependency_requires_auth_when_enabled() -> None:
    test_app = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TEST,
            auth_enabled=True,
            admin_api_key=SecretStr("correct-key"),
        )
    )

    @test_app.get(
        "/permission-test",
        dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
    )
    async def permission_test() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/permission-test")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
