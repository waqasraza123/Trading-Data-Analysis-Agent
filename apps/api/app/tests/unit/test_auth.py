from typing import cast
from uuid import uuid4

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppEnvironment, Settings
from app.main import create_app
from app.modules.auth.api_keys import api_key_prefix, generate_api_key, hash_api_key
from app.modules.auth.identity import IdentityContext
from app.modules.auth.passwords import (
    generate_session_token,
    hash_legacy_password,
    hash_password,
    hash_session_token,
    password_needs_rehash,
    verify_password,
)
from app.modules.auth.routes import update_auth_profile
from app.modules.auth.schemas import AuthProfileUpdateRequest, IdentitySource
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission
from app.modules.users.models import User, UserRole


def test_api_key_hash_does_not_store_raw_key() -> None:
    raw_key = generate_api_key()
    hashed_key = hash_api_key(raw_key)

    assert raw_key.startswith("tai_")
    assert hashed_key != raw_key
    assert hash_api_key(raw_key) == hashed_key
    assert api_key_prefix(raw_key) == raw_key[:16]


def test_password_hash_verification_does_not_store_raw_password() -> None:
    raw_password = "correct horse battery staple"
    password_hash = hash_password(raw_password)

    assert raw_password not in password_hash
    assert verify_password(raw_password, password_hash)
    assert not verify_password("incorrect horse battery", password_hash)
    assert password_hash.startswith("$argon2id$")
    assert not password_needs_rehash(password_hash)


def test_legacy_password_hash_remains_verifiable_and_requires_rehash() -> None:
    raw_password = "correct horse battery staple"
    password_hash = hash_legacy_password(raw_password)

    assert password_hash.startswith("pbkdf2_sha256$")
    assert verify_password(raw_password, password_hash)
    assert password_needs_rehash(password_hash)


def test_session_token_hash_does_not_store_raw_token() -> None:
    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)

    assert raw_token.startswith("tai_session_")
    assert token_hash != raw_token
    assert hash_session_token(raw_token) == token_hash


@pytest.mark.asyncio
async def test_profile_update_changes_only_authenticated_user_name() -> None:
    user = User(
        id=uuid4(),
        workspace_id=uuid4(),
        email="analyst@example.test",
        name="Original name",
        role=UserRole.ADMIN.value,
    )
    identity = IdentityContext(source=IdentitySource.SESSION, user=user, admin=True)
    session = cast(AsyncSession, ProfileSession())

    result = await update_auth_profile(
        AuthProfileUpdateRequest(name="  Updated name  "),
        identity,
        session,
    )

    assert user.name == "Updated name"
    assert user.email == "analyst@example.test"
    assert result.user is not None
    assert result.user.name == "Updated name"


class ProfileSession:
    async def flush(self) -> None:
        return None

    async def refresh(self, instance: object) -> None:
        return None

    async def commit(self) -> None:
        return None


def test_identity_workspace_mismatch_denies_access() -> None:
    workspace_id = uuid4()
    identity = IdentityContext(
        source=IdentitySource.DEV,
        user=User(
            id=uuid4(),
            workspace_id=workspace_id,
            email="analyst@example.test",
            name="Analyst",
            role=UserRole.ANALYST.value,
        ),
    )

    assert identity.can_access_workspace(workspace_id)
    assert not identity.can_access_workspace(uuid4())


def test_identity_missing_permission_denies_access() -> None:
    identity = IdentityContext(
        source=IdentitySource.DEV,
        user=User(
            id=uuid4(),
            workspace_id=uuid4(),
            email="analyst@example.test",
            name="Analyst",
            role=UserRole.ANALYST.value,
        ),
    )

    assert identity.has_permission(Permission.SCANS_WRITE)
    assert not identity.has_permission(Permission.CREDENTIALS_ADMIN)


@pytest.mark.asyncio
async def test_auth_me_dev_mode_without_headers_returns_guest_context() -> None:
    test_app = create_app(Settings(_env_file=None, app_env=AppEnvironment.TEST))

    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["authenticated"] is False


@pytest.mark.asyncio
async def test_protected_dependency_requires_auth_without_database() -> None:
    test_app = create_app(
        Settings(
            _env_file=None,
            app_env=AppEnvironment.TEST,
            auth_mode="api_key",
            auth_enabled=True,
            admin_api_key=SecretStr("correct-key"),
        )
    )

    @test_app.post(
        "/auth-protected-test",
        dependencies=[Depends(require_permission(Permission.CREDENTIALS_ADMIN))],
    )
    async def auth_protected_test() -> dict[str, str]:
        return {"status": "ok"}

    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        missing_response = await client.post("/auth-protected-test")
        legacy_response = await client.post(
            "/auth-protected-test",
            headers={"x-admin-api-key": "correct-key"},
        )
        configured_response = await client.post(
            "/auth-protected-test",
            headers={"x-api-key": "correct-key"},
        )

    assert missing_response.status_code == 401
    assert missing_response.json()["error"]["code"] == "authentication_required"
    assert legacy_response.status_code == 200
    assert configured_response.status_code == 200
