# Frontend E2E Harness

Load for: Playwright stack setup, `--e2e-ci`, Compose service selection, RQ readiness, screenshots, traces, or slow E2E startup.

## Harness Contracts

- Ordinary stack-backed tests start Core, Redis, and the internal scripted demo chat provider. A selected, non-skipped `e2e_full_stack` test activates the `rq` profile (worker, cron, testdata server). Mark every worker/cron-dependent test accordingly.
- Local sessions create and remove an isolated Compose project with fresh SQLite/Redis state and random host ports. Core readiness uses `/isalive`; full-stack startup additionally waits for authenticated RQ worker registration. Endpoint probes can degrade `/health`, so it does not gate stack readiness. RQ fixtures also check cron leadership.
- HTTP test services use matching `DEBUG=true` / `FLASK_DEBUG=1` so production Secure cookies and HSTS do not interfere with the isolated HTTP stack. Production cookie/header behavior has dedicated request-level coverage.
- The frontend runs in a session-scoped spawned Werkzeug process. `pytest-flask`'s fork-based live server is unsafe with native threads on Python 3.14; the separate process also isolates Core requests from per-test HTTP mocks.
- Worker prepares the shared RQ environment once; cron waits for `.e2e-ready`.
- Authenticated page fixtures complete onboarding tasks; onboarding tests explicitly reset them.
- Local E2E servers enable Chat. The landing-page workflow's `demo_chat_provider` fixture assigns `demo-llm` to Chat temporarily and seeds disposable stories; it skips external instances. The scripted Responses service returns search calls and answers from real search results without contacting an LLM, and accepts synthetic endpoint health probes.
- Demo teardown attempts endpoint deletion and news-item cleanup even when restoring the Chat assignment or deleting the endpoint fails. Removing the last news item also removes its story.
- `dev/testpipeline.sh` prepares component environments, then runs one complete E2E suite alongside lint/unit tests. CI likewise runs the full suite in one job; disposable GitHub runners skip container teardown.
- `--e2e-ci` omits documentation screenshots and successful-test traces. CI reruns failures with unique traces under `test-results/e2e-traces/`; unconditional tracing adds substantial teardown cost.
- `dev/record_workflow_video.py` records the full user workflow into a temporary `TARANIS_E2E_VIDEO_DIR`, then joins clips with FFmpeg stream copy into `taranis-walkthrough-video.webm`. It prints the output path and the destination under the `taranis.ai` repository's `static/` directory. The browser-context fixture writes `clips.jsonl` in page/test order after closing contexts; do not infer clip order from random filenames or file timestamps. Direct pytest recordings retain the ordinary raw-video destination.
- Recorded viewports match the 1920×1080 video size. The basic-user guard verifies the admin endpoint's 403 with a browser-context HTTP request, keeping access-denied screens out of recordings.

## Entry Points

- Harness: `src/frontend/tests/playwright/e2e_harness.py`, `src/frontend/tests/playwright/conftest.py`
- Services/readiness: `src/frontend/tests/playwright/compose.e2e.yml`, `src/frontend/tests/playwright/rq_e2e_fixtures.py`
- Helpers: `src/frontend/tests/playwright/playwright_helpers.py`
- HTMX waits: `htmx_helpers.py` tracks requests through `htmx:finally:request`, after HTMX 4 processes swapped content. `test_user_assess` covers Share after card replacement and asserts the dialog opens without navigation. Do not gate settlement on swap/process timestamp ordering: swaps without new elements need no process event.
- Commands: `src/frontend/tests/playwright/README.md`; CI: `.github/workflows/linting.yaml`

## Harness Diagnostics

From `src/frontend`, minimal-stack smoke targets `tests/playwright/test_e2e_admin.py::TestEndToEndAdmin::test_login`; full-stack smoke targets `tests/playwright/test_e2e_rq_tasks.py`. Run with `uv run pytest <target> --e2e-ci`. Render `tests/playwright/compose.e2e.yml` both with and without `--profile rq` when changing service selection. Feature signoff remains the [full pipeline](development-workflow.md#feature-signoff-loop).
