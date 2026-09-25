# Browser Security

## When To Load

Production cookies, response headers, CSP, API documentation assets, or embedded product previews.

## Contracts

- Core and frontend initialize browser security after loading app configuration. `DEBUG=false` forces JWT/CSRF and Flask session cookies to use `Secure`; `DEBUG=true` permits HTTP development. The old `JWT_COOKIE_SECURE` environment override no longer applies. Keep both services' DEBUG settings aligned; when using the Flask CLI, keep `FLASK_DEBUG` aligned too.
- Access JWT and session cookies remain HttpOnly. CSRF cookies remain readable by JavaScript. Cookies use SameSite=Lax so external login/navigation continues to work.
- Outside DEBUG, both apps add HSTS (one year), nosniff, SAMEORIGIN framing, strict-origin-when-cross-origin referrers, and a policy disabling camera, microphone, and geolocation. HSTS deliberately omits includeSubDomains and preload because deployments may share a hostname/domain with other services.
- Dynamic responses, including errors and downloads, use `Cache-Control: no-store`. Public static assets retain Flask's cache/revalidation behavior. Core's explicit published-report sandbox CSP is preserved.
- Core's default CSP denies resource loads. Frontend restricts loads to its origin, allowing HTTPS images and data/blob previews. PDF previews use an iframe so `object-src 'none'` can block plugins.
- Frontend CSP retains `unsafe-inline` scripts/styles and `unsafe-eval` for existing templates, Swagger initialization, HTMX, and standard Alpine. This is a compatibility policy, not a strict XSS-prevention CSP. Removing these allowances requires migrating inline handlers/scripts and the Alpine evaluator, including HTMX partial updates. Keep source restrictions and the public-report sandbox intact during that work.
- No automatic HTTPS redirect is performed by Flask: TLS termination and HTTP-to-HTTPS redirects belong to the deployment's trusted ingress. DEBUG is only for isolated development/test environments.

## Dependency Finding G4

`src/frontend/pyproject.toml` -> `swagger-ui-py-x` 26.2.18 -> its bundled `swagger_ui/static/swagger-ui-bundle.js` -> DOMPurify 3.2.6. The Python dependency is Ben's [swagger-ui-py fork](https://github.com/b3n4kh/swagger-ui-py). DOMPurify is embedded JavaScript, so Python dependency audits and adding a separate npm dependency do not replace it.

As checked on 2026-09-25, the fork's latest PyPI release is still 26.2.18. Refresh the fork's Swagger UI assets with its `tools/update.py --ui --ui-version <release>` command, inspect the resulting bundle's DOMPurify version against upstream advisories, publish a new wrapper release, then update `swagger-ui-py-x` and regenerate the frontend uv lockfile. Swagger UI v5.33.0's actual prebuilt bundle embeds DOMPurify 3.4.13; DOMPurify's latest release is 3.4.16. Rebuilding Swagger UI with a patched DOMPurify is necessary if its prebuilt bundle remains affected. WeasyPrint is already locked to 70.0 in the worker.

## Entry Points and Validation

`src/core/core/security.py`, `src/frontend/frontend/security.py`, both app factories, and the Publish product template. Coverage: core `tests/unit/test_security.py`, frontend `tests/unit/test_auth_cookie_config.py`, existing auth/publishing tests, and the full signoff pipeline. HTTP E2E services explicitly enable DEBUG.

Guidance: [Flask security](https://flask.palletsprojects.com/en/stable/web-security/), [OWASP HTTP headers](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html), [Alpine CSP requirements](https://alpinejs.dev/advanced/csp).
