# Authentication And Identity

The API now has a production auth abstraction under `app.modules.auth`. It keeps local developer flows working while adding a clear path for first-party password sessions, JWT providers, persisted API keys, workspace membership checks, and RBAC enforcement.

## Modes

- `AUTH_MODE=dev`: local/test mode. `x-user-id` and `x-workspace-id` may provide context. With `AUTH_ENABLED=false`, protected dependencies remain a local pass-through.
- `AUTH_MODE=session`: protected routes require a `Bearer tai_session_*` token created by `POST /auth/login` or `POST /auth/register`.
- `AUTH_MODE=api_key`: protected routes require an API key. Persisted keys are hashed in `auth_api_keys`; the legacy `ADMIN_API_KEY` remains supported.
- `AUTH_MODE=jwt`: protected routes require `Authorization: Bearer <token>` and `AUTH_JWT_ENABLED=true`.
- `AUTH_MODE=mixed`: password sessions are preferred, JWT is accepted next, and API keys are accepted as fallback.

`AUTH_ENABLED=true` remains a compatibility switch for the legacy admin API-key model. For new production deployments, prefer setting `AUTH_MODE` explicitly.

## Settings

- `AUTH_MODE=dev`
- `AUTH_ENABLED=false`
- `AUTH_JWT_ENABLED=false`
- `AUTH_API_KEYS_ENABLED=true`
- `AUTH_PASSWORD_ENABLED=true`
- `AUTH_PASSWORD_SIGNUP_ENABLED=true`
- `AUTH_SESSION_TTL_MINUTES=1440`
- `AUTH_PASSWORD_FAILED_ATTEMPT_LIMIT=8`
- `AUTH_PASSWORD_LOCKOUT_MINUTES=15`
- `AUTH_DEV_USER_EMAIL=`
- `AUTH_DEV_WORKSPACE_ID=`
- `JWT_ISSUER=`
- `JWT_AUDIENCE=`
- `JWT_PUBLIC_KEY=`
- `JWT_ALGORITHM=RS256`
- `API_KEY_HEADER_NAME=x-api-key`
- `USER_CONTEXT_HEADER_NAME=x-user-id`
- `WORKSPACE_CONTEXT_HEADER_NAME=x-workspace-id`

JWT verification currently supports RS256 with a configured PEM public key. OAuth/session providers such as Auth.js, Clerk, Supabase Auth, or a custom issuer should link their provider subject into `auth_identities`.

## Password Sessions

Password credentials are stored in `auth_password_credentials` with PBKDF2-SHA256 hashes and never return raw passwords. Sessions are stored in `auth_sessions` as SHA-256 token hashes with expiry and revocation state. `POST /auth/register` creates a workspace, admin user, password credential, and session. `POST /auth/login` creates a new session for an existing credential. `POST /auth/logout` revokes the supplied bearer token.

Session management endpoints are available for first-party password sessions:

- `GET /auth/sessions` lists up to 100 authenticated-user session records by default, with `limit` bounded to 200, without exposing token hashes.
- `POST /auth/sessions/{session_id}/revoke` revokes one session owned by the authenticated user.
- `POST /auth/sessions/revoke-other` revokes the authenticated user's other active sessions while preserving the current bearer session when it can be resolved.
- `POST /auth/password/change` verifies the current password, stores a new PBKDF2-SHA256 hash, clears failed-attempt lock state after a valid current password, and can revoke other active sessions while keeping the current session.

These endpoints require a password-session identity. API keys and legacy admin keys are intentionally not a substitute for user-session and password management.

Use a Neon Postgres `DATABASE_URL` and run Alembic migrations before enabling `AUTH_MODE=session` in deployed environments.

## API Keys

Persisted API keys store only `key_hash` and `key_prefix`. The raw key is returned once from `POST /auth/api-keys`.

API-key statuses are `active`, `disabled`, `revoked`, and `expired`. Keys may be workspace-scoped or global. Scopes can contain permission names such as `scans.write`; `*` grants admin-equivalent access.

## Identity And Workspace Isolation

The current identity resolves to a user, workspace, provider subject, API key, scopes, and permissions. Workspace access is denied when the request workspace does not match the resolved user workspace or workspace-scoped API key.

`GET /auth/me` returns the resolved identity. `GET /auth/context` returns auth mode/settings metadata safe for clients.

## Safety Boundary

This auth layer only protects market-intelligence APIs. It does not add broker execution, copy trading, auto-trading, external signal delivery, or financial-advice behavior.
