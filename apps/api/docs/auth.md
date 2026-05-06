# Authentication And Identity

The API now has a production auth abstraction under `app.modules.auth`. It keeps local developer flows working while adding a clear path for JWT providers, persisted API keys, workspace membership checks, and RBAC enforcement.

## Modes

- `AUTH_MODE=dev`: local/test mode. `x-user-id` and `x-workspace-id` may provide context. With `AUTH_ENABLED=false`, protected dependencies remain a local pass-through.
- `AUTH_MODE=api_key`: protected routes require an API key. Persisted keys are hashed in `auth_api_keys`; the legacy `ADMIN_API_KEY` remains supported.
- `AUTH_MODE=jwt`: protected routes require `Authorization: Bearer <token>` and `AUTH_JWT_ENABLED=true`.
- `AUTH_MODE=mixed`: JWT is preferred and API keys are accepted as fallback.

`AUTH_ENABLED=true` remains a compatibility switch for the legacy admin API-key model. For new production deployments, prefer setting `AUTH_MODE` explicitly.

## Settings

- `AUTH_MODE=dev`
- `AUTH_ENABLED=false`
- `AUTH_JWT_ENABLED=false`
- `AUTH_API_KEYS_ENABLED=true`
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

## API Keys

Persisted API keys store only `key_hash` and `key_prefix`. The raw key is returned once from `POST /auth/api-keys`.

API-key statuses are `active`, `disabled`, `revoked`, and `expired`. Keys may be workspace-scoped or global. Scopes can contain permission names such as `scans.write`; `*` grants admin-equivalent access.

## Identity And Workspace Isolation

The current identity resolves to a user, workspace, provider subject, API key, scopes, and permissions. Workspace access is denied when the request workspace does not match the resolved user workspace or workspace-scoped API key.

`GET /auth/me` returns the resolved identity. `GET /auth/context` returns auth mode/settings metadata safe for clients.

## Safety Boundary

This auth layer only protects market-intelligence APIs. It does not add broker execution, copy trading, auto-trading, external signal delivery, or financial-advice behavior.
