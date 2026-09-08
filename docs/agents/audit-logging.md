# Audit Logging

## When To Load

Audit/security/request/login logs, `core.audit`, or `AUDIT_LOG_ENABLED`.

## Contracts

Core emits JSONL to stdout for human JWT-authenticated API POST/PUT/PATCH/DELETE requests and login. API-key-only worker/bot activity and GET exports are excluded. Retention/search belong to the log collector, not the application database.

Records contain only timestamp, method, path, endpoint, status, user/organization IDs, username, client IP, and route IDs. Never include bodies, credentials, content, or before/after values. IP comes from trusted Flask `request.remote_addr`; proxy normalization must happen before the hook, which must not parse raw forwarded headers.

The hook is registered once, honors the environment toggle, and logs failures without changing the response.

## Entry Points and Coverage

`src/core/core/audit.py`, `src/core/core/managers/api_manager.py`, `src/core/core/config.py`, `src/core/core/auth/database_authenticator.py`.

Tests: `src/core/tests/application/mixed_flows/security/test_audit.py`, `src/core/tests/application/mixed_flows/security/test_auth.py`.
