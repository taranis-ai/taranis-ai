# Frontend E2E Harness

## When To Load

Frontend Playwright tests, `--e2e-ci`, `compose.e2e.yml`, pytest-docker fixtures, RQ E2E tests, CI browser lanes, tracing, screenshots, or slow E2E startup.

## Expected Behavior

The harness starts Core and Redis for ordinary stack-backed browser tests. It activates worker, cron, and the testdata server only when a selected `e2e_full_stack` test requires them. Default local runs use an isolated Compose project and clean it up. The complete local signoff pipeline passes `--e2e-keep-stack` and deliberately reuses the named full `taranis-e2e` project across fix-and-rerun attempts.

`--e2e-ci` never records documentation screenshots or successful-test traces. CI runs the complete E2E suite in one job, then reruns only failures with tracing enabled and stores unique trace files under `test-results/e2e-traces/`.

## Code Paths

- Harness and service selection: `src/frontend/tests/playwright/e2e_harness.py`, `src/frontend/tests/playwright/conftest.py`
- Compose services: `src/frontend/tests/playwright/compose.e2e.yml`
- RQ readiness: `src/frontend/tests/playwright/rq_e2e_fixtures.py`
- Browser helpers: `src/frontend/tests/playwright/playwright_helpers.py`
- CI job: `.github/workflows/linting.yaml`
- Developer commands: `src/frontend/tests/playwright/README.md`

## Data Flow

pytest-docker creates an isolated project, publishes Core and Redis on random host ports, and waits for Core's liveness endpoint. RQ fixtures separately verify worker registration and cron leadership. In `auto` mode, any selected, non-skipped `e2e_full_stack` item activates the Compose `rq` profile; otherwise the harness targets only Core.

The frontend test app runs in a session-scoped spawned Werkzeug process. Do not replace it with `pytest-flask`'s process-based live server: its required `fork()` start method is unsafe once native threads exist on Python 3.14. Keep the separate process boundary because it also isolates frontend Core requests from per-test HTTP mocks.

CI runs the complete frontend E2E suite in one job and lets automatic service selection start the full stack when the collected tests require it. This keeps the CI command equivalent to a full local run and makes failures easier to reproduce. GitHub-hosted runners do not spend time stopping containers because the runner itself is disposable. Authenticated page fixtures mark the relevant onboarding tasks complete before opening a page; the onboarding tests explicitly reset those tasks when they need the unfinished state.

`dev/testpipeline.sh` prepares all component environments first, then runs one complete E2E suite alongside component lint and unit tests. Before reusing an existing stack, it restarts Core, worker, and cron so bind-mounted Python changes are loaded without discarding containers, dependency environments, SQLite, or Redis state.

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
- Do not run local signoff pipelines concurrently because every invocation shares the `taranis-e2e` project and its state.
- Do not tear down the stack after an ordinary feature failure; retaining it is what speeds up the next complete signoff attempt.
- Do not make tracing unconditional. Recording and compressing a trace for every successful test is a major teardown cost.
- Do not move worker/cron-dependent assertions into a Core-only lane.
- Mark every worker/cron-dependent browser test with `e2e_full_stack`; `auto` service selection deliberately depends on that marker.
- Application-backed tests that use the session browser directly must request `e2e_browser` so the frontend server is running before the browser opens a page.
