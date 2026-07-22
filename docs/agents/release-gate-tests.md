# Release Gate Tests

## When To Load
Release gate tests, load tests, PostgreSQL TLS smoke tests, Docker Compose release validation, GHCR `latest` images, `.github/workflows/release_gate.yml`, `docker/run_release_gate_tests.sh`, `docker/compose-variations/compose.load.yml`.

## Expected Behavior
Release gates run against already published images, defaulting to `ghcr.io/taranis-ai/*:latest`. They must not build application images. The GitHub Actions workflow takes no inputs, checks out the current `master`, and runs PostgreSQL TLS multiprocess validation followed by the load test with the repository defaults. The load gate seeds synthetic stories and reports and completes onboarding for the test user before Locust starts. Locust flow failures remain visible in the results but do not fail the gate; setup and runner errors remain fatal.

## Code Paths
- `docker/run_release_gate_tests.sh`
- `docker/test_core_postgres_tls_multiprocess.sh`
- `docker/compose_command.sh`
- `docker/postgres-tls/`
- `docker/compose-variations/compose.load.yml`
- `.github/workflows/release_gate.yml`
- `docker/README.md`

## Data Flow
The workflow checks out `master` and invokes the release-gate runner without arguments, which selects all gates. The runner exports shared image defaults, resolves the Compose command through `docker/compose_command.sh`, then dispatches named shell gates. The TLS gate creates temporary PostgreSQL certs, then uses `docker/compose.yml` plus `docker/compose.core-postgres-tls.yml`; static TLS entrypoint/init scripts live in `docker/postgres-tls/`. The load gate uses `docker/compose-variations/compose.load.yml`, runs the load-test image's seed module, and then starts Locust. The workflow uploads the captured release-gate output together with Locust HTML, CSV, and screenshot artifacts from `LOAD_ARTIFACT_DIR`.

## Testing
Run `bash -n docker/compose_command.sh docker/run_release_gate_tests.sh docker/test_core_postgres_tls_multiprocess.sh`. Render the load compose config and confirm the seed service uses the published load-test image and release app services have `image` entries with no `build` blocks. When Docker is available, run `./docker/run_release_gate_tests.sh postgres-tls` and `./docker/run_release_gate_tests.sh load`.

## Pitfalls
Do not add workflow inputs or reintroduce `build:` in release-gate compose files. Keep Locust's result-error exit code at zero so individual flow failures remain diagnostic rather than release-blocking. `latest` means the already published master image set, so run the gate after those images are available and before tagging a release.
