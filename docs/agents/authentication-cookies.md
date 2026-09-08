# Authentication Cookies

## When To Load

Login/logout, JWT/CSRF cookies, implicit renewal, `JWT_COOKIE_SUFFIX`, `APPLICATION_ROOT`, or `TARANIS_BASE_PATH`.

## Contracts

- Core/frontend must share the literal `JWT_COOKIE_SUFFIX` and base path for all auth cookies (core `APPLICATION_ROOT`, frontend `TARANIS_BASE_PATH`). The suffix defaults to empty and accepts letters, digits, `_`, and `-`. Same-domain deployments need distinct suffixes; introducing one requires affected sessions to log in again.
- Login records `last_login` and a `LOGIN` activity, then issues access JWT/CSRF cookies. There are no refresh tokens/cookies.
- Frontend renews authenticated access tokens within 30 minutes of expiry via core and explicitly forwards `Set-Cookie` headers. Ordinary Core API responses do not forward them automatically.
- `GET /api/auth/refresh` accepts bearer access tokens, rejects cookie-only/revoked tokens, and issues replacements without recording another login. Core alone owns issuance/revocation checks.
- Logout, rejected renewal, and expiration clear the configured names and paths.
- Realtime connect authentication uses a dedicated cookie-validating proxy; see [Realtime Events](realtime-events.md). Do not disable browser CSRF checks to accommodate EventSource.

## Entry Points and Coverage

Settings: `src/core/core/config.py`, `src/frontend/frontend/config.py`. Issuance/validation: `src/core/core/auth/base_authenticator.py`, `src/core/core/api/auth.py`, `src/core/core/managers/auth_manager.py`. Frontend forwarding/clearing: `src/frontend/frontend/auth.py`; cookie consumers include `core_api.py`, `data_persistence.py`, templates, and `static/js/main.js` under `src/frontend/frontend/`.

Settings/auth coverage must retain empty/suffixed names, invalid suffixes, deployment paths, expiry-window renewal, bearer-only refresh, revocation, and absence of login side effects on renewal.
