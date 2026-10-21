# Playwright guide

## Running tests

### Run fast tests in headless mode

From `src/frontend` folder run:

```bash
pytest --e2e-ci
```

The E2E harness starts and stops a dedicated Docker/Podman Compose test stack automatically for the session.
Core is started from a plain Python container with `src/core` mounted, so Core code changes are picked up without image rebuilds.
The harness starts Core, Redis, and a scripted demo chat provider unless a selected `e2e_full_stack` test also requires the worker, cron, and testdata services.
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
- `--highlight-delay=<float>` - control time (seconds) to highlight elements in the video (pytest default: `0`; recording script default: `2`)
- `--e2e-trace` - record unique traces for stack-backed browser tests
- `-s` - see all logs on stdout

### Record the landing-page workflow

From the repository root, create one final WebM of the complete analyst workflow, including Chat:

```bash
./dev/record_workflow_video.py
```

Requires `uv`, `ffmpeg`, and the normal Playwright/Compose test setup. The script runs all workflow tests,
joins the clips in workflow order without re-encoding, and creates a 1920×1080 WebM. It prints the absolute path and copy instruction:

```text
Video created -> it is here: /path/to/taranis-ai/src/frontend/tests/playwright/videos/taranis-walkthrough-video.webm
Now copy to 'taranis.ai' repository under 'static/taranis-walkthrough-video.webm'
```

Use `--output /path/to/demo.webm` to choose the destination, or `--highlight-delay=0` for a quick run instead of the default two-second highlights.
Clips are recorded in a temporary directory and removed after the run. An existing final video is replaced only after the tests and encoding succeed.
The script requires the isolated local stack so the Chat segment always uses the scripted provider.

To keep separate raw clips instead, run from `src/frontend`:

```bash
uv run pytest tests/playwright/test_e2e_workflow.py --e2e-user-workflow --record-video --highlight-delay=2
```

To record only the Chat segment:

```bash
uv run pytest tests/playwright/test_e2e_workflow.py::TestUserWorkflow::test_chat --e2e-user-workflow --record-video --highlight-delay=2
```

Direct pytest recording saves a WebM per browser page under `tests/playwright/videos/`. The script above joins clips automatically.
The Assess segment keeps triage brief: review two stories, mark them read, then flag those same stories as important. Detailed filtering, bulk actions, clustering, and editing remain covered by the regular user E2E workflows.
The Chat segment shows a ransomware search, an unread follow-up, reopening saved history, clicking the matching-stories link, and opening a source story in Assess to inspect the evidence.
It uses the real frontend, Core search, and conversation persistence with three disposable demo stories.
Only the provider is scripted (`fixtures/chat_provider.py`, the internal `demo-llm` Compose service): no credentials or real LLM calls are needed.
Chat is enabled in the local E2E servers. The fixture temporarily assigns the demo provider only to Chat and restores the assignment afterward.
The demo is skipped against external instances, so recording cannot reconfigure their providers. Successful runs remove their demo conversation and stories.
Chat uses the same highlight helper and instant form filling as the other segments: `--highlight-delay=0` adds no typing or reading delays; a positive delay highlights the controls, answer bubbles, evidence link, and source content for that duration. Headless CI also runs this workflow without highlights or pauses.

### Record the SBOM PoC walkthrough

`test_e2e_asset_sbom.py` exercises the same workflow in CI and in a recorded demonstration:
import a host SBOM, review grouped inventory and installation paths, and immediately see
matching intelligence after the automatic historical scan. Each article appears once with a
compact software summary; expand **Why this matches** to see both installed versions and
their shared evidence. Follow supporting articles in Assess,
then optionally refine matching across both BuildKit versions with one rule. It also checks that collection updates refresh evidence and disabling
triggers removes matches. Refreshing the results keeps open explanations expanded while
replacing their content with current evidence.

The walkthrough uses only repository fixtures in a fresh isolated Compose stack:

- `src/core/tests/test_data/sbom/test-sbom-import.cdx.json`: a small CycloneDX inventory
  retaining representative BuildKit versions and installation paths from the external host
  sample. Five software records group into four components; one individual file is excluded.
  It includes duplicate installations, two BuildKit versions, curl, and a component without CPEs.
- `tests/playwright/testdata/sbom-news-items.json`: two synthetic security articles (one
  matching the title, one the body), an unrelated partial product name, a community article,
  and a curl advisory. Four stories match immediately after import. Optional context and
  activation changes narrow the results to the two security articles. The test ingests the
  fixtures before creating the asset, so the automatic historical scan is necessary.

The second workflow demonstrates imported findings, SBOM replacement and the cross-host intelligence overview. It imports a second host without scores, then filters by CVE and package-name matching, score availability, CVSS range, host and package. It verifies that each article appears once, source-specific package scores stay associated, and expanded details survive refresh. It uses
`test-sbom-findings.cdx.json` with illustrative CVEs, multiple sources and ratings,
exact component references and a supplied analysis. It adds small generated findings to
exercise the 50-ID CTI pages, searches for BuildKit, expands source details, disables CVE
matching independently, and updates the asset while preserving that decision. Its article
fixture supplies the existing CVE tag; IOC extraction remains the responsibility of IOC Bot.

From `src/frontend`, record with readable pauses and highlighted controls:

```bash
uv run pytest tests/playwright/test_e2e_asset_sbom.py \
  --e2e-user-workflow --record-video --highlight-delay=1.5 --e2e-timeout=15000 -s
```

This opens Chromium. On Linux without a display, prefix `uv run` with
`xvfb-run -a -s '-screen 0 1920x1080x24'`. Leave `TARANIS_E2E_EXTERNAL_*` variables unset
so the harness uses its isolated services. No local database, external SBOM, or collected
advisory is needed. The test removes its asset and articles, and the harness removes the stack.

Each workflow saves its 1920×1080 recording and screenshots under
`tests/playwright/videos/sbom-showcase-<suffix>/`, with the video named `sbom-showcase.webm`.
The tests print their separate recording paths. To record only findings and replacement, add `-k findings_cti`. Artifacts stay ignored by Git.

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
