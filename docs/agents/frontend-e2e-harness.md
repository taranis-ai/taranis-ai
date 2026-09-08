# Frontend E2E Harness

## When To Load

Playwright stack setup, `--e2e-ci`, Compose service selection, RQ readiness, screenshots, traces, or slow E2E startup.

## Harness Contracts

- Ordinary stack-backed tests start Core and Redis. A selected, non-skipped `e2e_full_stack` test activates the `rq` profile (worker, cron, testdata server). Mark every worker/cron-dependent test accordingly.
- Local sessions create and remove an isolated Compose project with fresh SQLite/Redis state and random host ports. Core readiness uses `/isalive`: aggregate `/health` is degraded without workers. RQ fixtures separately check worker registration and cron leadership.
- The frontend runs in a session-scoped spawned Werkzeug process. `pytest-flask`'s fork-based live server is unsafe with native threads on Python 3.14; the separate process also isolates Core requests from per-test HTTP mocks.
- Worker prepares the shared RQ environment once; cron waits for `.e2e-ready`.
- Authenticated page fixtures complete onboarding tasks; onboarding tests explicitly reset them.
- `dev/testpipeline.sh` prepares component environments, then runs one complete E2E suite alongside lint/unit tests. CI likewise runs the full suite in one job; disposable GitHub runners skip container teardown.
- `--e2e-ci` omits documentation screenshots and successful-test traces. CI reruns failures with unique traces under `test-results/e2e-traces/`; unconditional tracing adds substantial teardown cost.

## Entry Points

- Harness: `src/frontend/tests/playwright/e2e_harness.py`, `src/frontend/tests/playwright/conftest.py`
- Services/readiness: `src/frontend/tests/playwright/compose.e2e.yml`, `src/frontend/tests/playwright/rq_e2e_fixtures.py`
- Helpers: `src/frontend/tests/playwright/playwright_helpers.py`
- Commands: `src/frontend/tests/playwright/README.md`; CI: `.github/workflows/linting.yaml`

## Harness Diagnostics

From `src/frontend`, minimal-stack smoke targets `tests/playwright/test_e2e_admin.py::TestEndToEndAdmin::test_login`; full-stack smoke targets `tests/playwright/test_e2e_rq_tasks.py`. Run with `uv run pytest <target> --e2e-ci`. Render `tests/playwright/compose.e2e.yml` both with and without `--profile rq` when changing service selection. Feature signoff remains the [full pipeline](development-workflow.md#feature-signoff-loop).
