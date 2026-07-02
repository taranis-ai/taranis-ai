# End-to-end load testing

Manual browser end-to-end load testing for Taranis AI using Locust and `locust-plugins` Playwright users.

## What it does

- starts a disposable Docker stack with `ingress`, `core`, `frontend`, PostgreSQL, and Redis
- seeds synthetic sources, stories, report types, and reports
- runs low-concurrency browser flows against `/frontend/login`, `/frontend/`, `/frontend/assess`, and `/frontend/analyze`
- stores Locust reports, CSV stats, compose logs, and seed logs under `src/frontend/tests/load/artifacts/`

## Local usage

From the repository root:

```bash
./dev/run_e2e_load_tests.sh --profile smoke
./dev/run_e2e_load_tests.sh --profile browser_load --users 4 --spawn-rate 1 --run-time 10m
./dev/run_e2e_load_tests.sh --profile smoke --flows login,dashboard
./dev/run_e2e_load_tests.sh --profile browser_load --assess-count 2000 --report-count 500
./dev/run_e2e_load_tests.sh --profile browser_load --device-read-iops=/dev/sda:500 --device-write-iops=/dev/sda:500
```

The runner prints the artifact directory and the main Locust output paths at startup. At the end of each run it updates `src/frontend/tests/load/artifacts/latest` to point at the run artifacts and prints a direct `file://` link to the latest Locust report.

Runner flow:

- Docker Compose starts the disposable database, Redis, core, frontend, and ingress stack.
- The host runner runs `tests.load.load_support.seed` against the exposed ingress API to create synthetic sources, stories, report types, and reports.
- The `locust` service runs `locustfile.py` and writes standard Locust HTML and CSV artifacts.

Defaults:

- `smoke`: `1` browser user, `1/s`, `2m`
- `browser_load`: `4` browser users, `1/s`, `10m`
- seeded data:
  - `1000` stories for Assess
  - `250` reports for Analyze
  - `10` OSINT sources
  - `5` report types

Optional seed sizing:

- `--assess-count N` or `--story-count N`
- `--report-count N`
- environment overrides:
  - `LOAD_TEST_STORY_COUNT`
  - `LOAD_TEST_REPORT_COUNT`

Optional PostgreSQL IOPS throttling:

- `--device-read-iops=/dev/sda:500`
- `--device-write-iops=/dev/sda:500`
- use the real host block device path; one could use `lsblk`, `/dev/sda` is only an example

Optional E2E-derived flow selection:

- `--flows login,dashboard,assess_list`
- supported flow names:
  - `login`
  - `dashboard`
  - `assess_list`
  - `assess_detail`
  - `analyze_list`
  - `analyze_report_detail`

Artifacts are written to a timestamped directory below `src/frontend/tests/load/artifacts/`.
The runner writes `locust-report.html`, `locust_stats.csv`, `locust_failures.csv`, `locust_exceptions.csv`, `seed.log`, `locust-console.log`, `compose.log`, and `compose-ps.txt` when those outputs are available.

Open the latest HTML report directly from disk:

```bash
xdg-open src/frontend/tests/load/artifacts/latest/locust-report.html
```

## Reading the Locust report

- Each Locust row represents one browser flow task, such as `FrontendSelectedE2EFlowUser.assess_list_flow`.
- The `Aggregated` row combines all browser flow task events over the whole run.
- `RPS` is Locust task events per second, not backend HTTP requests per second.

Feature-specific local test:

```bash
cd src/frontend/tests/load && DEBUG=true uv run pytest test_frontend_flows.py
cd src/frontend/tests/load && DEBUG=true uv run pytest test_seed_data.py
```

## Notes

- This harness is intentionally browser-first and user-workspace-only.
- Seed data is treated as disposable for this harness. Rerunning the seed step against the same database may create additional rows instead of updating previous seeded records.
- It does not include `worker` or `cron` in the load-test stack.
- The Locust user class is generated from the load-test flow registry.
