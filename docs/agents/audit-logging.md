# Audit Logging

## When To Load

Load this memory for tasks mentioning audit logs, audit events, security logging, request logging, login logging, `/api/auth/login`, `core.audit`, or `AUDIT_LOG_ENABLED`.

## Expected Behavior

Core audit logging is a small v1 feature. It emits one JSON line to stdout for human JWT-authenticated `POST`, `PUT`, `PATCH`, and `DELETE` API requests, plus `/api/auth/login`.

Audit records are metadata only: timestamp, method, path, endpoint, status, user id, username, organization id, client IP, and route ids. Do not log request bodies, credentials, tokens, connector secrets, story content, or before/after values.

## Code Paths

- Core audit hook: `src/core/core/audit.py`
- App registration: `src/core/core/managers/api_manager.py`
- Settings: `src/core/core/config.py`
- Login failure logging: `src/core/core/auth/database_authenticator.py`
- Tests: `src/core/tests/application/mixed_flows/security/test_audit.py`

## Data Flow

`api_manager.initialize()` registers the audit hook once with Flask. The hook runs after each request, checks the env toggle, method, API path, and actor, then writes a JSON object to stdout. Audit failures are logged but do not change the API response.

## Testing

Primary validation:

- `cd src/core && uv run pytest tests/application/mixed_flows/security/test_audit.py tests/application/mixed_flows/security/test_auth.py`
- `cd src/core && uv run ruff check`
- `cd src/core && ./dev/check_touched_pyright.sh`

## Pitfalls

- Keep v1 out of the database; retention and search belong to the log collector.
- Do not add per-route policy config until an operator has a concrete requirement.
- API-key-only worker and bot routes are intentionally not audited as human activity.
- `GET` exports are intentionally not audited in v1.
