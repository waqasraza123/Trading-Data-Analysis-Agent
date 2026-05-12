import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.errors import AppError
from app.modules.auth.identity import IdentityContext
from app.modules.auth.models import (
    AuthIdentityStatus,
    AuthPasswordCredential,
    AuthSession,
    AuthSessionStatus,
)
from app.modules.auth.schemas import IdentitySource
from app.modules.users.models import User, UserRole
from app.modules.workspaces.models import Workspace

PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 210_000
SESSION_TOKEN_PREFIX = "tai_session_"


@dataclass(frozen=True)
class CreatedSession:
    token: str
    expires_at: datetime
    identity: IdentityContext


class PasswordAuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def register(
        self,
        *,
        workspace_name: str,
        name: str,
        email: str,
        password: str,
    ) -> CreatedSession:
        if not self.settings.auth_password_enabled:
            raise AppError(404, "password_auth_disabled", "Password authentication is disabled")
        if not self.settings.auth_password_signup_enabled:
            raise AppError(403, "signup_disabled", "Sign-up is disabled")
        normalized_email = normalize_email(email)
        normalized_name = normalize_required_text(name, "name")
        normalized_workspace_name = normalize_required_text(workspace_name, "workspace_name")
        password_hash = hash_password(password)
        workspace_id = uuid4()
        user_id = uuid4()
        workspace = Workspace(id=workspace_id, name=normalized_workspace_name)
        user = User(
            id=user_id,
            workspace_id=workspace_id,
            email=normalized_email,
            name=normalized_name,
            role=UserRole.ADMIN.value,
        )
        credential = AuthPasswordCredential(
            user_id=user_id,
            workspace_id=workspace_id,
            email=normalized_email,
            password_hash=password_hash,
            status=AuthIdentityStatus.ACTIVE.value,
            failed_attempts=0,
        )
        self.session.add(workspace)
        self.session.add(user)
        self.session.add(credential)
        try:
            await self.session.flush()
            created_session = await self.create_session(user=user, workspace=workspace)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(409, "account_conflict", "Account already exists") from error
        return created_session

    async def login(self, *, email: str, password: str) -> CreatedSession:
        if not self.settings.auth_password_enabled:
            raise AppError(404, "password_auth_disabled", "Password authentication is disabled")
        normalized_email = normalize_email(email)
        credential = await self.get_credential_by_email(normalized_email)
        if credential is None:
            raise invalid_credentials_error()
        now = datetime.now(UTC)
        if credential.status != AuthIdentityStatus.ACTIVE.value:
            raise invalid_credentials_error()
        if credential.locked_until is not None and credential.locked_until > now:
            raise AppError(423, "account_locked", "Account is temporarily locked")
        if not verify_password(password, credential.password_hash):
            await self.record_failed_attempt(credential, now)
            raise invalid_credentials_error()
        user = await self.session.get(User, credential.user_id)
        workspace = await self.session.get(Workspace, credential.workspace_id)
        if user is None or workspace is None or user.workspace_id != workspace.id:
            raise invalid_credentials_error()
        credential.failed_attempts = 0
        credential.locked_until = None
        credential.last_login_at = now
        created_session = await self.create_session(user=user, workspace=workspace)
        await self.session.commit()
        return created_session

    async def resolve_session(self, token: str) -> IdentityContext | None:
        if not self.settings.auth_password_enabled:
            return None
        token_hash = hash_session_token(token)
        statement = select(AuthSession).where(
            AuthSession.token_hash == token_hash,
            AuthSession.status == AuthSessionStatus.ACTIVE.value,
        )
        result = await self.session.execute(statement)
        auth_session = result.scalar_one_or_none()
        if auth_session is None:
            return None
        now = datetime.now(UTC)
        if auth_session.expires_at <= now:
            auth_session.status = AuthSessionStatus.EXPIRED.value
            await self.session.commit()
            return None
        user = await self.session.get(User, auth_session.user_id)
        workspace = await self.session.get(Workspace, auth_session.workspace_id)
        if user is None or workspace is None or user.workspace_id != workspace.id:
            return None
        auth_session.last_seen_at = now
        await self.session.commit()
        return IdentityContext(
            source=IdentitySource.SESSION,
            user=user,
            workspace=workspace,
            admin=user.role == UserRole.ADMIN.value,
        )

    async def revoke_session(self, token: str) -> None:
        token_hash = hash_session_token(token)
        statement = select(AuthSession).where(
            AuthSession.token_hash == token_hash,
            AuthSession.status == AuthSessionStatus.ACTIVE.value,
        )
        result = await self.session.execute(statement)
        auth_session = result.scalar_one_or_none()
        if auth_session is None:
            return
        auth_session.status = AuthSessionStatus.REVOKED.value
        await self.session.commit()

    async def change_password(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        current_password: str,
        new_password: str,
        revoke_other_sessions: bool,
        current_token: str | None,
    ) -> int:
        if not self.settings.auth_password_enabled:
            raise AppError(404, "password_auth_disabled", "Password authentication is disabled")
        credential = await self.get_credential_by_user(
            user_id=user_id,
            workspace_id=workspace_id,
        )
        if credential is None or credential.status != AuthIdentityStatus.ACTIVE.value:
            raise AppError(404, "password_credential_not_found", "Password credential was not found")
        now = datetime.now(UTC)
        if credential.locked_until is not None and credential.locked_until > now:
            raise AppError(423, "account_locked", "Account is temporarily locked")
        if not verify_password(current_password, credential.password_hash):
            await self.record_failed_attempt(credential, now)
            raise invalid_credentials_error()
        if verify_password(new_password, credential.password_hash):
            raise AppError(422, "password_unchanged", "New password must be different")
        credential.password_hash = hash_password(new_password)
        credential.failed_attempts = 0
        credential.locked_until = None
        revoked_count = 0
        if revoke_other_sessions:
            await self.expire_stale_user_sessions(
                user_id=user_id,
                workspace_id=workspace_id,
                commit=False,
            )
            revoked_count = await self.mark_other_user_sessions_revoked(
                user_id=user_id,
                workspace_id=workspace_id,
                current_token=current_token,
            )
        await self.session.commit()
        return revoked_count

    async def list_user_sessions(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        limit: int,
    ) -> list[AuthSession]:
        await self.expire_stale_user_sessions(user_id=user_id, workspace_id=workspace_id)
        result = await self.session.execute(
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.workspace_id == workspace_id,
            )
            .order_by(AuthSession.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def revoke_user_session(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        workspace_id: UUID,
    ) -> AuthSession:
        await self.expire_stale_user_sessions(user_id=user_id, workspace_id=workspace_id)
        result = await self.session.execute(
            select(AuthSession).where(
                AuthSession.id == session_id,
                AuthSession.user_id == user_id,
                AuthSession.workspace_id == workspace_id,
            )
        )
        auth_session = result.scalar_one_or_none()
        if auth_session is None:
            raise AppError(404, "session_not_found", "Session was not found")
        if auth_session.status == AuthSessionStatus.ACTIVE.value:
            auth_session.status = AuthSessionStatus.REVOKED.value
            await self.session.commit()
            await self.session.refresh(auth_session)
        return auth_session

    async def revoke_other_user_sessions(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        current_token: str | None,
    ) -> int:
        await self.expire_stale_user_sessions(user_id=user_id, workspace_id=workspace_id)
        revoked_count = await self.mark_other_user_sessions_revoked(
            user_id=user_id,
            workspace_id=workspace_id,
            current_token=current_token,
        )
        if revoked_count > 0:
            await self.session.commit()
        return revoked_count

    async def mark_other_user_sessions_revoked(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        current_token: str | None,
    ) -> int:
        current_token_hash = hash_session_token(current_token) if current_token else None
        result = await self.session.execute(
            select(AuthSession).where(
                AuthSession.user_id == user_id,
                AuthSession.workspace_id == workspace_id,
                AuthSession.status == AuthSessionStatus.ACTIVE.value,
            )
        )
        revoked_count = 0
        for auth_session in result.scalars().all():
            if current_token_hash is not None and auth_session.token_hash == current_token_hash:
                continue
            auth_session.status = AuthSessionStatus.REVOKED.value
            revoked_count += 1
        return revoked_count

    async def create_session(self, *, user: User, workspace: Workspace) -> CreatedSession:
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=self.settings.auth_session_ttl_minutes)
        token = generate_session_token()
        auth_session = AuthSession(
            user_id=user.id,
            workspace_id=workspace.id,
            token_hash=hash_session_token(token),
            status=AuthSessionStatus.ACTIVE.value,
            expires_at=expires_at,
            last_seen_at=now,
        )
        self.session.add(auth_session)
        await self.session.flush()
        return CreatedSession(
            token=token,
            expires_at=expires_at,
            identity=IdentityContext(
                source=IdentitySource.SESSION,
                user=user,
                workspace=workspace,
                admin=user.role == UserRole.ADMIN.value,
            ),
        )

    async def get_credential_by_email(self, email: str) -> AuthPasswordCredential | None:
        result = await self.session.execute(
            select(AuthPasswordCredential).where(AuthPasswordCredential.email == email)
        )
        return result.scalar_one_or_none()

    async def get_credential_by_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
    ) -> AuthPasswordCredential | None:
        result = await self.session.execute(
            select(AuthPasswordCredential).where(
                AuthPasswordCredential.user_id == user_id,
                AuthPasswordCredential.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def record_failed_attempt(
        self,
        credential: AuthPasswordCredential,
        now: datetime,
    ) -> None:
        credential.failed_attempts += 1
        if credential.failed_attempts >= self.settings.auth_password_failed_attempt_limit:
            credential.locked_until = now + timedelta(
                minutes=self.settings.auth_password_lockout_minutes
            )
        await self.session.commit()

    async def expire_stale_user_sessions(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        commit: bool = True,
    ) -> int:
        now = datetime.now(UTC)
        result = await self.session.execute(
            select(AuthSession).where(
                AuthSession.user_id == user_id,
                AuthSession.workspace_id == workspace_id,
                AuthSession.status == AuthSessionStatus.ACTIVE.value,
                AuthSession.expires_at <= now,
            )
        )
        expired_count = 0
        for auth_session in result.scalars().all():
            auth_session.status = AuthSessionStatus.EXPIRED.value
            expired_count += 1
        if expired_count > 0 and commit:
            await self.session.commit()
        return expired_count


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if "@" not in normalized:
        raise AppError(422, "invalid_email", "Email must be valid")
    return normalized


def normalize_required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise AppError(422, f"invalid_{field_name}", "Required text is missing")
    return normalized


def hash_password(password: str) -> str:
    validate_password(password)
    salt = secrets.token_bytes(32)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return "$".join(
        (
            PASSWORD_HASH_ALGORITHM,
            str(PASSWORD_HASH_ITERATIONS),
            encode_part(salt),
            encode_part(digest),
        )
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_value, salt_value, digest_value = stored_hash.split("$", 3)
        iterations = int(iterations_value)
        salt = decode_part(salt_value)
        expected_digest = decode_part(digest_value)
    except (ValueError, TypeError):
        return False
    if algorithm != PASSWORD_HASH_ALGORITHM:
        return False
    supplied_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(supplied_digest, expected_digest)


def validate_password(password: str) -> None:
    if len(password) < 12:
        raise AppError(422, "weak_password", "Password must be at least 12 characters")
    if len(password) > 256:
        raise AppError(422, "weak_password", "Password is too long")


def generate_session_token() -> str:
    return f"{SESSION_TOKEN_PREFIX}{secrets.token_urlsafe(48)}"


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def encode_part(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def decode_part(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def invalid_credentials_error() -> AppError:
    return AppError(401, "invalid_credentials", "Credentials are invalid")
