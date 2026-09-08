# PizzINT Dashboard

## When To Load

PizzINT, DOUGHCON, `/dashboard/pizzint`, or `show_pizzint`.

## Contracts

- Disabled by default and enabled per user. Load the card through an authenticated HTMX partial after the dashboard; upstream latency must not delay the main page.
- Show level/readiness, smoothed index, and observation time, plus attribution, all five levels, and the informational-use disclaimer. The API retains the upstream reason but the card omits it.
- Core fetches a fixed upstream URL with epoch-millisecond `_t`, validates the response, and uses Redis keys for fresh (10 minutes), last-good (1 hour), and failed-refresh suppression (1 minute).
- Accept only explicit `fresh`/`stale` values and timezone-aware UTC timestamps. Unknown freshness or upstream/cache failures use last-good or a static unavailable state. No collector/history model is involved.

## Entry Points and Coverage

`src/core/core/service/pizzint.py`, `src/core/core/api/dashboard.py`, `src/models/models/dashboard.py`, `src/models/models/user.py`, `src/frontend/frontend/views/dashboard_views.py`.

Tests: `src/core/tests/application/user_workspace/test_dashboard_pizzint.py`, `src/core/tests/test_api.py`, `src/frontend/tests/unit/views/test_views.py`. Mock the upstream; tests must not depend on live PizzINT.
