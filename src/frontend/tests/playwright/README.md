# Playwright guide

## Running tests

### Run fast tests in headless mode

From `src/frontend` folder run:

```bash
pytest --e2e-ci
```

The E2E harness starts and stops a dedicated Docker Compose stack for the test session.

Core runtime modes:
- `fast` (default locally): runs Core from a plain Python container with `src/core` mounted, so code changes are picked up without rebuilding.
- `production` (default in CI): builds Core from `docker/Containerfile.core` and runs it with Postgres and RabbitMQ sidecars.
- `external`: run tests against an already running stack (for example smoke-test compose).

Use `TARANIS_E2E_CORE_MODE=fast` or `TARANIS_E2E_CORE_MODE=production` to override.
For `external` mode set:
- `TARANIS_E2E_EXTERNAL_BASE_URL` (for example `http://127.0.0.1:8080/frontend`)
- `TARANIS_E2E_EXTERNAL_CORE_URL` (for example `http://127.0.0.1:8080/api`)
- `TARANIS_E2E_EXTERNAL_API_KEY` (required when seeding via worker API on external stacks)
- optional `TARANIS_E2E_EXTERNAL_AUTH_USERNAME` / `TARANIS_E2E_EXTERNAL_AUTH_PASSWORD` (defaults: `admin` / `admin`)
- optional `TARANIS_E2E_EXTERNAL_NON_ADMIN_AUTH_USERNAME` / `TARANIS_E2E_EXTERNAL_NON_ADMIN_AUTH_PASSWORD` (if omitted, tests provision a temporary non-admin user via API)

You only need Docker/Compose available locally.

### Run tests in headful mode

From `src/frontend` folder run:

```bash
pytest --e2e-admin
```

All flags:

- `--e2e-ci` - e2e tests of user and admin parts (headless)
- `--e2e-admin` - end to end tests of admin section; generate pictures for documentation (also User sections)
- `--record-video` - record a video (save to `src/core/tests/playwright/videos`)
- `--highlight-delay=<float>` - control time (seconds) to highlight elements in the video (`default=2`)
- `-s` - see all logs on stdout

## Use Playwright Codegen tool to generate tests

```bash
playwright codegen --viewport-size=1920,1080 localhost:<port>
```

To use the preseeded test instance for writing tests, place:

```python
page.pause()

```

Where desired, to stop the test execution and allow to connect to the instance with Codegen tool.

## Debug mode

To enter the debug mode, use:

```bash
PWDEBUG=1 pytest <--flag>
```

To halt a test at a certain point, use classic breakpoints, or place `page.pause()` where you want the debugger to stop (works also without `PWDEBUG=1`).

## Pictures for documentation

To generate most of the pictures for documentation, run:

```bash
pytest --e2e-admin
```

To copy the pictures to the documentation repository, use [this](https://github.com/taranis-ai/taranis.ai/blob/master/scripts/sync_new_pictures.sh) script.

It takes two arguments:

```bash
./sync_new_pictures.sh <path/to/screenshot/folder_in_taranis-ai> <path_to_taranis.ai/static/docs>
```

Script has variables to influence dest. subdirectories of respective pictures. Change as needed.

## Data Storage for E2E

- In `fast` mode, Core uses an internal SQLite file inside its container for each test session.
- In `production` mode, Core uses ephemeral Postgres and RabbitMQ containers.

No manual cleanup is required.
