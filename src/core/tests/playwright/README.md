# Playwright guide

## Running tests
### Run fast tests in headless mode
From `src/core` folder run:
```bash
pytest --run-e2e-ci
```

### Run tests in headful mode
From `src/core` folder run:
```bash
pytest --run-e2e
```

Other flags:
- `--produce-artifacts` - record a video (save to `src/core/tests/playwright/videos`)
- `--highlight-delay=<float>` - control time (seconds) to highlight elements in the video (`default=2`)
- `-s` - see all logs on stdout

## Use Playwright Codegen tool to generate tests
```bash
playwright codegen --viewport-size=1920,1080 localhost:<port>
```

To use the preseeded test instance for writing tests, place:

```python
expect(page).to_have_title("Uncomment and halt test run for test writing purposes", timeout=0)

```
where desired, to stop the test execution and allow to connect to the instance with Codegen tool.

## Debug mode
To enter the debug mode use:
```bash
PWDEBUG=1 pytest --run-e2e
```
To halt a test at a certain point, use classic breakpoints, or place `page.pause()` where you want the debugger to stop.