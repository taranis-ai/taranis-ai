# Frontend E2E Harness

## When To Load

Frontend Playwright tests, `--e2e-ci`, `compose.e2e.yml`, pytest-docker fixtures, RQ E2E tests, CI browser lanes, tracing, screenshots, or slow E2E startup.

## Expected Behavior

The harness starts Core and Redis for ordinary stack-backed browser tests. It activates worker, cron, and the testdata server only when a selected `e2e_full_stack` test requires them. Default local runs use an isolated Compose project and clean it up; `--e2e-keep-stack` deliberately reuses the named `taranis-e2e` project for a fast edit-test loop.

`--e2e-ci` never records documentation screenshots or successful-test traces. CI reruns only failures with tracing enabled and stores unique trace files under `test-results/e2e-traces/`.

## Code Paths

- Harness and service selection: `src/frontend/tests/playwright/e2e_harness.py`, `src/frontend/tests/playwright/conftest.py`
- Compose services: `src/frontend/tests/playwright/compose.e2e.yml`
- RQ readiness: `src/frontend/tests/playwright/rq_e2e_fixtures.py`
- Browser helpers: `src/frontend/tests/playwright/playwright_helpers.py`
- CI lanes: `.github/workflows/linting.yaml`
- Developer commands: `src/frontend/tests/playwright/README.md`

## Data Flow

pytest-docker creates an isolated project, publishes Core and Redis on random host ports, and waits for Core's liveness endpoint. RQ fixtures separately verify worker registration and cron leadership. In `auto` mode, any selected, non-skipped `e2e_full_stack` item activates the Compose `rq` profile; otherwise the harness targets only Core.

CI runs two admin shards, one user shard, one application-backed support shard, one browser-only JavaScript shard, and one RQ/dashboard shard concurrently. Each lane uses a distinct Compose project name. GitHub-hosted runners do not spend time stopping containers because the runner itself is disposable. Authenticated page fixtures mark the relevant onboarding tasks complete before opening a page; the onboarding tests explicitly reset those tasks when they need the unfinished state, so every shard can run independently.

Worker prepares the RQ virtual environment once and shares it with cron. Cron waits for the `.e2e-ready` marker instead of independently installing the same dependency graph.

## Testing

From `src/frontend`:

- Minimal stack smoke: `uv run pytest tests/playwright/test_e2e_admin.py::TestEndToEndAdmin::test_login --e2e-ci`
- Full stack smoke: `uv run pytest tests/playwright/test_e2e_rq_tasks.py --e2e-ci`
- Full serial comparison: `uv run pytest tests/playwright --e2e-ci --durations=40`
- Compose rendering: `docker compose -f tests/playwright/compose.e2e.yml config` and `docker compose --profile rq -f tests/playwright/compose.e2e.yml config`

## Pitfalls

- Core's aggregate `/health` endpoint is degraded when no worker is connected. Minimal browser lanes must wait for `/isalive`; RQ fixtures own worker and cron readiness checks.
- Reusable-stack mode preserves SQLite and Redis data. Use unique records, clean up fixtures, or reset the stack when state affects the result.
- Do not make tracing unconditional. Recording and compressing a trace for every successful test is a major teardown cost.
- Do not move worker/cron-dependent assertions into a Core-only lane.
- Mark every worker/cron-dependent browser test with `e2e_full_stack`; `auto` service selection deliberately depends on that marker.
- Application-backed tests that use the session browser directly must request `e2e_browser`. It forces Flask's forked live server to start before Playwright creates browser threads; reversing that order can deadlock teardown on Python 3.14.
