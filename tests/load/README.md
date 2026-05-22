# End-to-end load testing

Manual browser end-to-end load testing for Taranis AI using Locust and `locust-plugins` Playwright users.

## What it does

- starts a disposable Docker stack with `ingress`, `core`, `frontend`, PostgreSQL, and Redis
- seeds deterministic stories and reports
- runs low-concurrency browser flows against `/frontend/login`, `/frontend/`, `/frontend/assess`, and `/frontend/analyze`
- stores Locust reports, compose logs, recovery checks, and page-ready timing summaries under `tests/load/artifacts/`

## Local usage

From the repository root:

```bash
./dev/run_e2e_load_tests.sh --profile smoke
./dev/run_e2e_load_tests.sh --profile browser_load --users 4 --spawn-rate 1 --run-time 10m
./dev/run_e2e_load_tests.sh --profile smoke --flows login,dashboard
./dev/run_e2e_load_tests.sh --stop-report-server
```

The runner keeps the newest completed artifact set linked at `tests/load/artifacts/latest/`.
It also starts or reuses a small local HTTP server for `tests/load/artifacts/`, starting at `http://127.0.0.1:18081/` and moving to the next free port if needed.
The exact Locust report URL is printed by the runner, and the preferred starting port can be changed with `--report-port` or `LOAD_TEST_REPORT_PORT`.
Use `--stop-report-server` to stop that local HTTP server when you no longer need it.

Defaults:

- `smoke`: `1` browser user, `1/s`, `2m`
- `browser_load`: `4` browser users, `1/s`, `10m`

Optional E2E-derived flow selection:

- `--flows login,dashboard,assess_list`
- supported flow names:
  - `login`
  - `dashboard`
  - `assess_list`
  - `assess_detail`
  - `analyze_list`
  - `analyze_report_detail`

Artifacts are written to a timestamped directory below `tests/load/artifacts/`.
The newest HTML report is always linked at `tests/load/artifacts/latest/locust-report.html`.
The runner also writes:

- `ux-timings-summary.md` with Locust `PAGE` rows sorted by slowest `p95`
- `ux-timings-summary.json` with the same data in machine-readable form

## Reading the Locust report

- In this browser harness, the Locust HTML `Aggregated` row combines all recorded Locust events, not just one page type.
- That means it includes coarse `TASK` rows such as `FrontendBrowserUser.assess_flow` and custom `PAGE` rows such as `assess:ready`.
- The `Aggregated Min` value is the single fastest recorded event across the full report. It is not an average of per-row minimums.
- The `Aggregated RPS` value is total recorded Locust events per second over the whole run.
- In this harness, `RPS` is therefore not backend HTTP requests per second and not “browser sessions per second”.
- For example, when a flow records both one `TASK` event and one `PAGE` event, both count toward the aggregate request total.
- For user-facing performance analysis, prefer the `PAGE` rows and the generated `ux-timings-summary.md`.

Feature-specific local test:

```bash
cd tests/load && uv run pytest test_summarize_stats.py
cd tests/load && uv run pytest test_frontend_flows.py
```

## Notes

- This harness is intentionally browser-first and user-workspace-only.
- It does not include `worker` or `cron` in the baseline stack.
- The original PoC Locust tasks remain available; `--flows` adds an optional E2E-derived flow layer instead of replacing them.
- Locust keeps the coarse `TASK` rows and additionally records user-facing page readiness as `PAGE` rows:
  - `login:dashboard_ready`
  - `dashboard:ready`
  - `assess:ready`
  - `analyze:ready`
- When `--flows` is used, the load-enabled E2E-derived flows emit:
  - `login:ready`
  - `dashboard:ready`
  - `assess:list_ready`
  - `assess:detail_ready`
  - `analyze:list_ready`
  - `analyze:report_detail_ready`
- `/api/health` is compared against the pre-load baseline instead of assuming a healthy `200`, because the current core health model reports worker availability when Redis is configured.
