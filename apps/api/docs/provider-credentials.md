# Provider Credential References

Provider credentials are represented as workspace-scoped references, not raw secret values. The
backend stores enough metadata to answer whether a provider or delivery channel is configured,
active, paused, revoked, missing, or failing tests without exposing API keys, tokens, passwords, or
webhook signing secrets.

This module is for data providers and delivery channels only. It does not add broker credentials,
broker order execution, auto-trading, copy trading, or financial-advice workflows.

## Storage Model

`provider_credential_refs` stores:

- `workspace_id`
- `name`
- `provider`
- `credential_type`
- `status`
- `secret_ref`
- `public_metadata_json`
- last connection-test status, timestamp, and safe error message
- `rotated_at`

`secret_ref` is an opaque pointer such as `env:POLYGON_API_KEY`, `vault:market/polygon`, or a future
secret-manager path. It is not the secret itself and is not resolved in this phase.

`public_metadata_json` may contain non-secret fields such as auth type, scopes, region, or masked
fingerprints. Inline secret-shaped keys such as token, password, authorization, bearer, api key, and
secret are rejected or redacted by module helpers.

## Connection Tests

`provider_connection_tests` records safe test attempts:

- `configuration_only`
- `mock`
- `public_endpoint`
- `authenticated_endpoint`

Mock providers pass without external calls or secrets. `none_required` providers can run public
endpoint tests only when `PROVIDER_CREDENTIAL_ALLOW_PUBLIC_TESTS=true`. Authenticated endpoint tests
are skipped unless `PROVIDER_CREDENTIAL_ALLOW_AUTH_TESTS=true`, and raw secret resolution is still
not implemented in this phase.

Request and response metadata is redacted before persistence. Test metadata never includes raw
secret values.

## API

```txt
POST /provider-credentials
GET /provider-credentials
GET /provider-credentials/{credential_ref_id}
PATCH /provider-credentials/{credential_ref_id}
POST /provider-credentials/{credential_ref_id}/pause
POST /provider-credentials/{credential_ref_id}/revoke
POST /provider-credentials/{credential_ref_id}/test
POST /provider-credentials/test-provider
GET /provider-credentials/tests/{test_id}
```

Credential read responses expose `secretRefConfigured` and `secretRefSummary`, not raw secret
values.

## Integration Points

Nullable `credential_ref_id` columns are available on:

- `data_sources`
- `live_feed_subscriptions`
- `provider_polling_requests`
- `notification_channels`
- `webhook_subscriptions`

These references are optional and backward-compatible. Existing mock providers and public Binance
polling continue to work without credentials.

## Settings

```txt
PROVIDER_CREDENTIALS_VERSION=v1
PROVIDER_CREDENTIAL_TEST_TIMEOUT_SECONDS=10
PROVIDER_CREDENTIAL_ALLOW_PUBLIC_TESTS=true
PROVIDER_CREDENTIAL_ALLOW_AUTH_TESTS=false
```

Credentials are not required at startup. Future secret-manager integration can resolve `secret_ref`
inside provider-specific adapters without changing public API contracts.
