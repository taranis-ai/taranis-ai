# Playwright guide

## Running tests

### Run fast tests in headless mode

From `src/frontend` folder run:

```bash
pytest --e2e-ci
```

The E2E harness starts and stops a dedicated Docker/Podman Compose test stack automatically for the session.
Core is started from a plain Python container with `src/core` mounted, so Core code changes are picked up without image rebuilds.
The harness starts only Core and Redis unless a selected `e2e_full_stack` test requires the worker, cron, and testdata services.
You need Docker Compose or Podman Compose available locally. For Podman, install `podman` and either `podman-compose` or a working `podman compose` provider.
The same frontend-owned test root also contains the RQ/Redis integration E2E suite.
The frontend test app runs in a spawned Werkzeug server process. This avoids Python 3.14's unsafe `fork()` behavior in
multi-threaded test processes while preserving process isolation from test HTTP mocks.

### Run tests in headful mode

From `src/frontend` folder run:

```bash
pytest --e2e-admin
```

All flags:

- `--e2e-ci` - e2e tests of user and admin parts (headless)
- `--e2e-admin` - end to end tests of admin section; generate pictures for documentation (also User sections)
- `--record-video` - record a video (save to `src/frontend/tests/playwright/videos`)
- `--highlight-delay=<float>` - control time (seconds) to highlight elements in the video (`default=2`)
- `--e2e-trace` - record unique traces for stack-backed browser tests
- `-s` - see all logs on stdout

### Run only the RQ/Redis integration E2E suite

From `src/frontend` folder run:

```bash
pytest tests/playwright/test_e2e_rq_tasks.py --e2e-ci
```

### Run the signoff pipeline

At the end of feature development, run the complete push-and-signoff pipeline from the repository root:

```bash
./dev/test_push_signoff.sh
```

`dev/testpipeline.sh` runs the complete Playwright suite in a fresh isolated Compose project and removes it after the test session. If the pipeline fails, fix and commit the problem, then run `./dev/test_push_signoff.sh` again. Do not substitute a focused Playwright target for the complete signoff rerun.

Successful CI runs do not record traces or documentation screenshots. Use `--e2e-trace` for a focused local trace; artifacts are written under `test-results/e2e-traces/`. CI automatically reruns failing tests with tracing enabled.

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

## Waiting for HTMX updates

Prefer Playwright locator assertions when the expected visible result fully describes the wait:

```python
expect(page.get_by_test_id("assess")).to_be_visible()
```

Use `with_htmx_wait(page, action)` when an action triggers HTMX and the next step reads or clicks DOM that may be swapped:

```python
with_htmx_wait(page, lambda: page.locator("#infinite-scroll-trigger").click())
```

Keep `page.expect_response(...)` for tests where the response itself is the behavior under test, such as downloads, imports, or settings submissions.

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

## Database for E2E

The local Playwright E2E stack runs Core against an ephemeral SQLite database and Redis-backed worker services.
No manual cleanup is required.
