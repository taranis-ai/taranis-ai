# Playwright guide

## Running tests

### Run fast tests in headless mode

From `src/core` folder run:

```bash
pytest --e2e-ci
```

### Run tests in headful mode

From `src/core` folder run:

```bash
pytest --e2e-user
```

All flags:

- `--e2e-user` - extensive tests of user parts (headful)
- `--e2e-ci` - e2e tests of user and admin parts (headless)
- `--e2e-user-workflow` - test of defined user workflow (headful)
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
PWDEBUG=1 pytest --e2e-ci
```

To always rebuild the VueJS gui set:

```bash
E2E_TEST_GUI_REBUILD=true pytest --e2e-ci
```

To halt a test at a certain point, use classic breakpoints, or place `page.pause()` where you want the debugger to stop (works also without `PWDEBUG=1`).

## Pictures for documentation

Has been moved to `src/frontend/tests/playwright`
