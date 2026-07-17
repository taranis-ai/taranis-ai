# Authentication Cookies

## When To Load

Authentication, login, logout, implicit JWT refresh, JWT cookies, CSRF cookies, `JWT_COOKIE_SUFFIX`, `APPLICATION_ROOT`, or `TARANIS_BASE_PATH`.

## Expected Behavior

- Core and frontend use the same literal `JWT_COOKIE_SUFFIX` for the access-token and access-CSRF cookie names.
- The suffix defaults to empty for backward-compatible root deployments and accepts only letters, digits, `_`, and `-`.
- All authentication cookies use the deployment base path. Core derives it from `APPLICATION_ROOT`; frontend uses `TARANIS_BASE_PATH`.
- Deployments sharing a domain must use unique suffixes, for example `_q` and `_p`.
- Authenticated frontend requests renew the access cookie when its token is within 30 minutes of expiry. No refresh token or refresh cookie is used.

## Code Paths

- Cookie configuration: `src/core/core/config.py` and `src/frontend/frontend/config.py`
- Token creation: `src/core/core/auth/base_authenticator.py`
- Implicit renewal and cookie clearing: `src/frontend/frontend/auth.py`
- Frontend cookie reads and clearing: `src/frontend/frontend/auth.py`, `core_api.py`, `data_persistence.py`, templates, and `static/js/main.js`

## Data Flow

Core creates the access JWT and its CSRF cookie. Frontend forwards the login `Set-Cookie` headers unchanged, reads the configured access cookie for core requests, and uses the configured CSRF cookie for forms and HTMX requests. On authenticated requests, a frontend `after_request` handler replaces access tokens that expire within 30 minutes. Flask-JWT-Extended clears the configured names and paths on logout or expiration.

## Testing

- Test empty and suffixed names, invalid suffixes, and both configured paths in core and frontend settings tests.
- Assert login and session clearing emit the configured names with the deployment path.
- Assert only access tokens within the renewal window are replaced.
- Run the full core, frontend, and frontend E2E test suites after authentication-cookie changes.

## Pitfalls

- Core and frontend suffixes or base paths must never differ within one deployment.
- Include the separator in the suffix (`_q`, not `q`) when readable cookie names matter.
- Existing subpath sessions require a new login when a suffix is introduced; root sessions using the empty suffix remain valid.
- Implicit renewal belongs in frontend because core responses pass through the frontend's server-side HTTP client, which does not forward ordinary `Set-Cookie` headers to the browser.
