# Backend Security

This phase adds operational security boundaries without changing deterministic market analysis.

## CORS

`CORS_ALLOWED_ORIGINS` accepts comma-separated origins:

```txt
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=false
```

CORS middleware is enabled only when origins are configured. Production rejects wildcard origins.
If production credentials are enabled, explicit origins are required.

## API Key Guard

Local and test default:

```txt
AUTH_ENABLED=false
```

When enabled, mutating routes require:

```txt
API_KEY_HEADER_NAME=x-admin-api-key
ADMIN_API_KEY=replace-with-secret-from-secret-manager
```

Health and readiness endpoints remain public. Read-only GET routes are not protected by this
temporary guard. This is an expansion point for real auth later, not OAuth or JWT.

## Rate Limit Foundation

```txt
RATE_LIMIT_ENABLED=false
RATE_LIMIT_REQUESTS_PER_MINUTE=60
```

Rate limiting is disabled by default to avoid local and test flakiness. When enabled, write routes
are limited by client host, method, and path. Health endpoints are excluded. The current fallback is
in-memory for local/test; production should use a Redis-backed implementation before enabling this
for multiple API instances.

## Request Limits

```txt
MAX_REQUEST_BODY_BYTES=1048576
MAX_UPLOAD_FILE_BYTES=10485760
```

Oversized JSON or multipart requests return a stable `413` error:

```json
{
  "error": {
    "code": "request_body_too_large",
    "message": "Request body is too large",
    "requestId": "..."
  }
}
```

The API checks `Content-Length` before route handling when available and applies a CSV upload
fallback check before import processing.

## Error Responses

Errors use:

```json
{
  "error": {
    "code": "...",
    "message": "...",
    "requestId": "..."
  }
}
```

Production responses do not expose tracebacks, raw SQL, request bodies, uploaded file content, or
secret values.
