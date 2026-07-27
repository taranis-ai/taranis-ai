# Authentication Cookies

## When To Load

Authentication, login, logout, implicit JWT refresh, JWT cookies, CSRF cookies, `JWT_COOKIE_SUFFIX`, `APPLICATION_ROOT`, or `TARANIS_BASE_PATH`.

## Expected Behavior

- Core and frontend use the same literal `JWT_COOKIE_SUFFIX` for the access-token and access-CSRF cookie names.
- The suffix defaults to empty for backward-compatible root deployments and accepts only letters, digits, `_`, and `-`.
- All authentication cookies use the deployment base path. Core derives it from `APPLICATION_ROOT`; frontend uses `TARANIS_BASE_PATH`.
- Deployments sharing a domain must use unique suffixes, for example `_q` and `_p`.
- Authenticated frontend requests renew the access cookie through core when its token is within 30 minutes of expiry. No refresh token or refresh cookie is used.
- `GET /api/auth/refresh` accepts bearer access tokens from the `Authorization` header for CLI and other non-browser clients.
- Successful authentication updates `last_login` and emits a `LOGIN` activity; access-token renewal does neither.

## Code Paths

- Cookie configuration: `src/core/core/config.py` and `src/frontend/frontend/config.py`
- Token creation: `src/core/core/auth/base_authenticator.py`
- Refresh and revocation validation: `src/core/core/api/auth.py` and `src/core/core/managers/auth_manager.py`
- Implicit renewal and cookie clearing: `src/frontend/frontend/auth.py`
- Frontend cookie reads and clearing: `src/frontend/frontend/auth.py`, `core_api.py`, `data_persistence.py`, templates, and `static/js/main.js`

## Data Flow

Core records successful authentication before creating the initial access JWT and its CSRF cookie. Frontend forwards the login `Set-Cookie` headers unchanged, reads the configured access cookie for core requests, and uses the configured CSRF cookie for forms and HTMX requests. On authenticated requests, a frontend `after_request` handler asks core to replace access tokens that expire within 30 minutes and forwards the returned `Set-Cookie` headers without recording another login. Core rejects revoked tokens before issuing replacements. Flask-JWT-Extended clears the configured names and paths on logout, rejected renewal, or expiration.

## Testing

- Test empty and suffixed names, invalid suffixes, and both configured paths in core and frontend settings tests.
- Assert login and session clearing emit the configured names with the deployment path.
- Assert only access tokens within the renewal window are replaced.
- Assert refresh accepts bearer headers, rejects cookie-only requests, and rejects revoked tokens.
- Assert refresh does not update `last_login` or emit a `LOGIN` activity.
- Run the full core, frontend, and frontend E2E test suites after authentication-cookie changes.

## Pitfalls

- Core and frontend suffixes or base paths must never differ within one deployment.
- Include the separator in the suffix (`_q`, not `q`) when readable cookie names matter.
- Existing subpath sessions require a new login when a suffix is introduced; root sessions using the empty suffix remain valid.
- Implicit renewal starts in frontend because ordinary core responses do not forward `Set-Cookie` headers to the browser; the frontend must forward the refresh response headers explicitly.
- Core owns refresh issuance and revocation checks. Frontend must not mint replacement access tokens locally.
