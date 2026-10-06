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
- `--highlight-delay=<float>` - control time (seconds) to highlight elements in the video (`default=0`)
- `--e2e-trace` - record unique traces for stack-backed browser tests
- `-s` - see all logs on stdout

### Record the SBOM PoC walkthrough

`test_e2e_asset_sbom.py` exercises the same workflow in CI and in a recorded demonstration:
import a host SBOM, review grouped inventory and installation paths, enable contextual
BuildKit triggers, scan historical articles through the real worker, and open supporting
intelligence in Assess. It also checks that collection updates refresh evidence and disabling
triggers removes matches.

The walkthrough uses only repository fixtures in a fresh isolated Compose stack:

- `src/core/tests/test_data/sbom/test-sbom-import.cdx.json`: a small CycloneDX inventory
  retaining representative BuildKit versions and installation paths from the external host
  sample. Five software records group into four components; one individual file is excluded.
  It includes duplicate installations, two BuildKit versions, curl, and a component without CPEs.
- `tests/playwright/testdata/sbom-news-items.json`: two synthetic matching articles (one
  matching the title, one the body) and three negative examples (partial product name,
  missing context, and disabled component rules). The test imports these through the worker
  ingestion API before creating the asset, so the historical scan is necessary.

From `src/frontend`, record with readable pauses and highlighted controls:

```bash
uv run pytest tests/playwright/test_e2e_asset_sbom.py \
  --e2e-user-workflow --record-video --highlight-delay=1.5 --e2e-timeout=15000 -s
```

This opens Chromium. On Linux without a display, prefix `uv run` with
`xvfb-run -a -s '-screen 0 1920x1080x24'`. Leave `TARANIS_E2E_EXTERNAL_*` variables unset
so the harness uses its isolated services. No local database, external SBOM, or collected
advisory is needed. The test removes its asset and articles, and the harness removes the stack.

The 1920×1080 recording and four screenshots are saved under
`tests/playwright/videos/sbom-showcase-<suffix>/`, with the video named `sbom-showcase.webm`.
The test prints the recording path. Artifacts stay ignored by Git.

To make an MP4 for manual sharing, run this inside the printed recording directory
(requires FFmpeg):

```bash
ffmpeg -i sbom-showcase.webm -c:v libx264 -crf 20 -pix_fmt yuv420p \
  -movflags +faststart sbom-showcase.mp4
```

For a quick run without recording or presentation pauses:

```bash
uv run pytest tests/playwright/test_e2e_asset_sbom.py --e2e-ci
```

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
