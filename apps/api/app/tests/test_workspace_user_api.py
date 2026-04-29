from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import UserRole
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService
from app.modules.workspaces.models import Workspace

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_workspace_api_persists_and_updates_data(api_client: AsyncClient) -> None:
    create_response = await api_client.post("/workspaces", json={"name": "  Desk A  "})

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "Desk A"

    list_response = await api_client.get("/workspaces")
    assert list_response.status_code == 200
    assert any(item["id"] == created["id"] for item in list_response.json())

    get_response = await api_client.get(f"/workspaces/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Desk A"

    patch_response = await api_client.patch(
        f"/workspaces/{created['id']}",
        json={"name": "Desk B"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "Desk B"


@pytest.mark.asyncio
async def test_workspace_api_returns_clean_missing_error(api_client: AsyncClient) -> None:
    response = await api_client.get(f"/workspaces/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "workspace_not_found"


@pytest.mark.asyncio
async def test_workspace_name_validation_rejects_blank_name(api_client: AsyncClient) -> None:
    response = await api_client.post("/workspaces", json={"name": "   "})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_user_api_validates_workspace_role_and_persists_data(
    api_client: AsyncClient,
    workspace: Workspace,
) -> None:
    create_response = await api_client.post(
        "/users",
        json={
            "workspaceId": str(workspace.id),
            "email": "  Analyst@Example.Test ",
            "name": " Analyst One ",
            "role": "analyst",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["workspaceId"] == str(workspace.id)
    assert created["email"] == "analyst@example.test"
    assert created["name"] == "Analyst One"
    assert created["role"] == "analyst"

    list_response = await api_client.get("/users", params={"workspace_id": str(workspace.id)})
    assert list_response.status_code == 200
    assert any(item["id"] == created["id"] for item in list_response.json())

    get_response = await api_client.get(f"/users/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "analyst@example.test"

    patch_response = await api_client.patch(
        f"/users/{created['id']}",
        json={"role": "admin", "name": "Admin One"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["role"] == "admin"
    assert patch_response.json()["name"] == "Admin One"


@pytest.mark.asyncio
async def test_user_create_under_missing_workspace_returns_clean_error(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        "/users",
        json={
            "workspaceId": str(uuid4()),
            "email": "missing@example.test",
            "name": "Missing Workspace User",
            "role": "user",
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "workspace_not_found"


@pytest.mark.asyncio
async def test_user_api_returns_clean_missing_error(api_client: AsyncClient) -> None:
    response = await api_client.get(f"/users/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "user_not_found"


@pytest.mark.asyncio
async def test_user_role_validation_rejects_unknown_role(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/users",
        json={
            "workspaceId": str(uuid4()),
            "email": "bad@example.test",
            "name": "Bad Role",
            "role": "owner",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_user_name_validation_rejects_blank_name(
    api_client: AsyncClient,
    workspace: Workspace,
) -> None:
    response = await api_client.post(
        "/users",
        json={
            "workspaceId": str(workspace.id),
            "email": "blank@example.test",
            "name": "   ",
            "role": "user",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_user_service_create_under_missing_workspace_fails(
    db_session: AsyncSession,
) -> None:
    from app.core.errors import AppError

    with pytest.raises(AppError) as error_info:
        await UserService(db_session).create_user(
            UserCreate(
                workspace_id=uuid4(),
                email="service@example.test",
                name="Service User",
                role=UserRole.USER,
            )
        )

    assert error_info.value.code == "workspace_not_found"
