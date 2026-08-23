# PizzINT Dashboard

## When To Load

PizzINT, DOUGHCON, external dashboard signals, `/dashboard/pizzint`, or the `show_pizzint` profile setting.

## Expected Behavior

- PizzINT is an opt-in user dashboard card and is disabled by default.
- The card shows the DOUGHCON level, its named readiness state, smoothed index, and observation time. The API retains the compact upstream reason, but the card does not render it.
- The card loads through HTMX after the main dashboard so an upstream timeout cannot delay the page.
- The information popover attributes PizzINT, explains all five DOUGHCON levels, and includes the informational-use disclaimer.
- Upstream or cache failures render a static unavailable state and never expose exception-derived text.

## Code Paths

- Shared response and profile models: `src/models/models/dashboard.py`, `src/models/models/user.py`
- Core fetch/cache service and endpoint: `src/core/core/service/pizzint.py`, `src/core/core/api/dashboard.py`
- Frontend view and templates: `src/frontend/frontend/views/dashboard_views.py`, `src/frontend/frontend/templates/dashboard/`
- API contract: `src/core/core/static/openapi3_1.yaml`

## Data Flow

When `show_pizzint` is enabled, the dashboard renders an HTMX placeholder that calls the authenticated frontend partial. The frontend loads `PizzintStatus` through `DataPersistenceLayer`, which calls the authenticated core endpoint. Core returns a shared Redis-cached result or fetches PizzINT with a current epoch-millisecond `_t` cache-buster. Redis expiration removes the fresh key after ten minutes and the last-good key after one hour; a one-minute refresh key prevents repeated failed refreshes.

## Testing

- Core fetch, validation, cache, retry, and stale behavior: `src/core/tests/application/user_workspace/test_dashboard_pizzint.py`
- Profile persistence: `src/core/tests/test_api.py`
- Dashboard opt-in, lazy loading, card states, and popover: `src/frontend/tests/unit/views/test_views.py`
- Automated tests must mock PizzINT and never depend on the live service.

## Pitfalls

Do not move the upstream request into the initial dashboard render or the browser. Keep the URL fixed server-side, validate the compact response at the trust boundary, preserve timezone-aware UTC timestamps, and keep exception text out of the API and card. Do not add a collector or persistence model unless history or downstream analysis is explicitly requested.
