import os
import pytest
import time
import subprocess
import requests
from dotenv import dotenv_values

from playwright.sync_api import Browser


def _wait_for_server_to_be_alive(url: str, timeout_seconds: int = 10):
    for _ in range(timeout_seconds):
        try:
            response = requests.get(url, timeout=timeout_seconds)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            time.sleep(0.5)
    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    return True


@pytest.fixture(scope="session")
def run_core(app):
    # run the flask core as a subprocess in the background
    process = None
    try:
        core_path = os.path.abspath("../core")
        env = {}
        if config := dotenv_values(os.path.join(core_path, "tests", ".env")):
            config = {k: v for k, v in config.items() if v}
            env = config
        env |= os.environ.copy()
        env["PYTHONPATH"] = core_path
        env["PATH"] = f"{os.path.join(core_path, '.venv', 'bin')}:{env.get('PATH', '')}"
        taranis_core_port = env.get("TARANIS_CORE_PORT", "5000")
        taranis_core_start_timeout = int(env.get("TARANIS_CORE_START_TIMEOUT", 10))
        print(f"Starting Taranis Core on port {taranis_core_port}")
        process = subprocess.Popen(
            ["flask", "run", "--no-reload", "--port", taranis_core_port],
            cwd=core_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        core_url = env.get("TARANIS_CORE_URL", f"http://127.0.0.1:{taranis_core_port}/api")
        print(f"Waiting for Taranis Core to be available at: {core_url}")
        _wait_for_server_to_be_alive(f"{core_url}/isalive", taranis_core_start_timeout)

        yield
    except Exception as e:
        pytest.fail(str(e))
    finally:
        if process:
            process.terminate()
            process.wait()


@pytest.fixture(scope="session")
def build_tailwindcss(app):
    # build the tailwind css
    try:
        if os.getenv("TARANIS_E2E_TEST_TAILWIND_REBUILD") == "true" or not os.path.isfile("frontend/static/css/tailwind.css"):
            result = subprocess.call(["./build_tailwindcss.sh"])
            assert result == 0, f"Install failed with status code: {result}"
    except Exception as e:
        pytest.fail(str(e))


@pytest.fixture(scope="class")
def e2e_ci(request):
    request.cls.ci_run = request.config.getoption("--e2e-ci") == "e2e_ci"
    request.cls.wait_duration = float(request.config.getoption("--highlight-delay"))

    if request.cls.ci_run:
        print("Running in CI mode")


@pytest.fixture(scope="session")
def e2e_server(app, live_server, build_tailwindcss, run_core):
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
