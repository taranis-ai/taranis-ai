import os
import pytest
import subprocess

from playwright.sync_api import Browser


@pytest.fixture(scope="session")
def run_core():
    # run the flask core as a subprocess in the background
    try:
        core_path = os.path.abspath("../core")
        env = os.environ.copy()
        env["PYTHONPATH"] = core_path
        env["PATH"] = f"{os.path.join(core_path, '.venv', 'bin')}:{env.get('PATH', '')}"
        process = subprocess.Popen(
            ["flask", "run"],
            cwd=core_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        yield process
        process.terminate()
        process.wait()
    except Exception as e:
        pytest.fail(str(e))


@pytest.fixture(scope="class")
def e2e_ci(request):
    request.cls.ci_run = request.config.getoption("--e2e-ci") == "e2e_ci"
    request.cls.wait_duration = float(request.config.getoption("--highlight-delay"))

    if request.cls.ci_run:
        print("Running in CI mode")


@pytest.fixture(scope="session")
def e2e_server(app, live_server, run_core):
    live_server.app = app
    live_server.start()
    yield live_server


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, browser_type_launch_args, request):
    browser_type_launch_args["args"] = ["--window-size=1964,1211"]

    if request.config.getoption("--e2e-admin"):
        browser_type_launch_args["args"] = ["--window-size=1640,1338"]

    if request.config.getoption("--record-video"):
        if request.config.getoption("--e2e-admin"):
            browser_type_launch_args["args"] = ["--window-size=1964,1211"]
            print("Screenshots in --e2e-admin mode are not of optimal resolution")
        return {
            **browser_context_args,
            "record_video_dir": "tests/playwright/videos",
            "no_viewport": True,
            "record_video_size": {"width": 1920, "height": 1080},
        }
    return {**browser_context_args, "no_viewport": True}


@pytest.fixture(scope="session")
def taranis_frontend(request, e2e_server, browser_context_args, browser: Browser):
    context = browser.new_context(**browser_context_args)
    # Drop timeout from 30s to 10s
    timeout = int(request.config.getoption("--e2e-timeout"))
    context.set_default_timeout(timeout)
    if request.config.getoption("--e2e-ci") == "e2e_ci":
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

    yield context.new_page()
    if request.config.getoption("--e2e-ci") == "e2e_ci":
        context.tracing.stop(path="taranis_ai_frontend_trace.zip")
