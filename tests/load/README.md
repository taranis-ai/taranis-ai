# Load testing

Manual browser load testing for Taranis AI using Locust and `locust-plugins` Playwright users.

## What it does

- starts a disposable Docker stack with `ingress`, `core`, `frontend`, PostgreSQL, and Redis
- seeds deterministic stories and reports
- runs low-concurrency browser flows against `/frontend/login`, `/frontend/`, `/frontend/assess`, and `/frontend/analyze`
- stores Locust reports, compose logs, and recovery checks under `tests/load/artifacts/`

## Local usage

From the repository root:

```bash
./dev/run_load_tests.sh --profile smoke
./dev/run_load_tests.sh --profile browser_load --users 4 --spawn-rate 1 --run-time 10m
```

Defaults:

- `smoke`: `1` browser user, `1/s`, `2m`
- `browser_load`: `4` browser users, `1/s`, `10m`

Artifacts are written to a timestamped directory below `tests/load/artifacts/`.

## Notes

- This harness is intentionally browser-first and user-workspace-only.
- It does not include `worker` or `cron` in the baseline stack.
- `/api/health` is compared against the pre-load baseline instead of assuming a healthy `200`, because the current core health model reports worker availability when Redis is configured.
