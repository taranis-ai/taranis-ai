# Release Gate Tests

## When To Load

Release gates, load testing, PostgreSQL TLS multiprocess validation, or published GHCR images.

## Contracts

The input-free workflow checks out current `master` and runs TLS validation, then load testing against published `ghcr.io/taranis-ai/*:latest` images. Never build application images here. Run after master images are available and before tagging a release.

The TLS gate creates temporary certificates. The load gate seeds synthetic stories/reports and completes user onboarding before Locust. Individual Locust flow failures are diagnostic (result-error exit code zero); setup/runner failures remain fatal. Upload captured output and Locust HTML/CSV/screenshots from `LOAD_ARTIFACT_DIR`.

## Entry Points and Validation

`.github/workflows/release_gate.yml`, `docker/run_release_gate_tests.sh`, `docker/compose_command.sh`, `docker/test_core_postgres_tls_multiprocess.sh`, `docker/postgres-tls/`, `docker/compose-variations/compose.load.yml`; operator reference: `docker/README.md`.

For gate changes, run `bash -n` on the scripts and render Compose to verify published images (including seed) and absence of `build:`. With Docker available, execute `./docker/run_release_gate_tests.sh postgres-tls` and `./docker/run_release_gate_tests.sh load`.
