# End-to-end load testing

Manual browser end-to-end load testing for Taranis AI using Locust and `locust-plugins` Playwright users.

## What it does

- starts a disposable Docker stack with `ingress`, `core`, `frontend`, PostgreSQL, and Redis
- seeds deterministic stories and reports
- runs low-concurrency browser flows against `/frontend/login`, `/frontend/`, `/frontend/assess`, and `/frontend/analyze`
- stores Locust reports, compose logs, and recovery checks under `tests/load/artifacts/`

## Local usage

From the repository root:

```bash
./dev/run_e2e_load_tests.sh --profile smoke
./dev/run_e2e_load_tests.sh --profile browser_load --users 4 --spawn-rate 1 --run-time 10m
./dev/run_e2e_load_tests.sh --stop-report-server
```

The runner keeps the newest completed artifact set linked at `tests/load/artifacts/latest/`.
It also starts or reuses a small local HTTP server for `tests/load/artifacts/`, starting at `http://127.0.0.1:18081/` and moving to the next free port if needed.
The exact Locust report URL is printed by the runner, and the preferred starting port can be changed with `--report-port` or `LOAD_TEST_REPORT_PORT`.
Use `--stop-report-server` to stop that local HTTP server when you no longer need it.

Defaults:

- `smoke`: `1` browser user, `1/s`, `2m`
- `browser_load`: `4` browser users, `1/s`, `10m`

Artifacts are written to a timestamped directory below `tests/load/artifacts/`.
The newest HTML report is always linked at `tests/load/artifacts/latest/locust-report.html`.

## Notes

- This harness is intentionally browser-first and user-workspace-only.
- It does not include `worker` or `cron` in the baseline stack.
- `/api/health` is compared against the pre-load baseline instead of assuming a healthy `200`, because the current core health model reports worker availability when Redis is configured.
