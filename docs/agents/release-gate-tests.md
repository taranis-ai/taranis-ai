# Release Gate Tests

## When To Load
Release gate tests, load tests, PostgreSQL TLS smoke tests, Docker Compose release validation, GHCR `latest` images, `.github/workflows/load_testing.yml`, `docker/run_release_gate_tests.sh`, `docker/compose-variations/compose.load.yml`.

## Expected Behavior
Release gates run against already published images, defaulting to `ghcr.io/taranis-ai/*:latest`. They must not build application images. The default gate runs PostgreSQL TLS multiprocess validation and then the load test.

## Code Paths
- `docker/run_release_gate_tests.sh`
- `docker/test_core_postgres_tls_multiprocess.sh`
- `docker/compose_command.sh`
- `docker/postgres-tls/`
- `docker/compose-variations/compose.load.yml`
- `.github/workflows/load_testing.yml`
- `docker/README.md`

## Data Flow
The release-gate runner exports shared image defaults, resolves the Compose command through `docker/compose_command.sh`, then dispatches named shell gates. The TLS gate creates temporary PostgreSQL certs, then uses `docker/compose.yml` plus `docker/compose.core-postgres-tls.yml`; static TLS entrypoint/init scripts live in `docker/postgres-tls/`. The load gate uses `docker/compose-variations/compose.load.yml` and writes Locust artifacts to `LOAD_ARTIFACT_DIR`.

## Testing
Run `bash -n docker/compose_command.sh docker/run_release_gate_tests.sh docker/test_core_postgres_tls_multiprocess.sh`. Render the load compose config and confirm release app services have `image` entries and no `build` blocks. When Docker is available, run `./docker/run_release_gate_tests.sh postgres-tls` and `./docker/run_release_gate_tests.sh load`.

## Pitfalls
Do not reintroduce `build:` in release-gate compose files. `latest` means the already published master image set, so run the gate after those images are available and before tagging a release.
