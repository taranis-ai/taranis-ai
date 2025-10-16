import os
import re
import pytest
import time
import subprocess
import requests
import responses
import contextlib
import warnings as pywarnings
from dotenv import dotenv_values
from urllib.parse import urlparse
from http.cookies import SimpleCookie

from playwright.sync_api import Browser, Page


def _wait_for_server_to_be_alive(url: str, timeout_seconds: int = 10):
    pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")
    responses.add_passthru(pattern)

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
        # Start with OS env and then overlay values from tests/.env so tests control the config
        env = os.environ.copy()
        if config := dotenv_values(os.path.join(core_path, "tests", ".env")):
            config = {k: v for k, v in config.items() if v is not None}
            env.update(config)
        env["PYTHONPATH"] = core_path
        env["PATH"] = f"{os.path.join(core_path, '.venv', 'bin')}:{env.get('PATH', '')}"
        taranis_core_port = env.get("TARANIS_CORE_PORT", "5000")
        taranis_core_start_timeout = int(env.get("TARANIS_CORE_START_TIMEOUT", 10))
        with contextlib.suppress(Exception):
            parsed_uri = urlparse(env.get("SQLALCHEMY_DATABASE_URI"))
            os.remove(f"{parsed_uri.path}")

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
def setup_test_templates():
    """Set up test template files for e2e tests."""
    import shutil
    from pathlib import Path

    # Get paths
    test_data_dir = Path(__file__).parent / "testdata"
    core_templates_dir = Path(__file__).parent.parent.parent.parent / "core" / "taranis_data" / "presenter_templates"

    # Ensure the core templates directory exists
    core_templates_dir.mkdir(parents=True, exist_ok=True)

    # Copy test template files
    copied_files = []
    for test_file in test_data_dir.glob("*.html"):
        dest_file = core_templates_dir / test_file.name
        shutil.copy2(test_file, dest_file)
        copied_files.append(dest_file)

    yield

    # Cleanup: remove test template files
    for file_path in copied_files:
        if file_path.exists():
            file_path.unlink()


@pytest.fixture(scope="session")
def taranis_frontend(request, e2e_server, setup_test_templates, browser_context_args, browser: Browser):
    context = browser.new_context(**browser_context_args)
    # Drop timeout from 30s to 10s
    timeout = int(request.config.getoption("--e2e-timeout"))
    context.set_default_timeout(timeout)
    if request.config.getoption("trace"):
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

    yield context.new_page()
    if request.config.getoption("trace"):
        context.tracing.stop(path="taranis_ai_frontend_trace.zip")


def _allowed(msg_text: str, allow_patterns: list[str]) -> bool:
    return any(re.search(p, msg_text) for p in allow_patterns)


def _cookies_from_response(resp) -> list[dict]:
    """Parse Flask Response `Set-Cookie` headers into Playwright cookie dicts (name/value/path only)."""
    cookies: list[dict] = []
    set_cookie_headers = resp.headers.getlist("Set-Cookie")
    for header in set_cookie_headers:
        c = SimpleCookie()
        c.load(header)
        cookies.extend(
            {
                "name": name,
                "value": morsel.value,
            }
            for name, morsel in c.items()
        )
    return cookies


@pytest.fixture
def logged_in_page(taranis_frontend: Page, e2e_server, access_token_response):
    """
    Returns a Playwright Page whose browser context has the JWT cookies set,
    so any navigation is already authenticated.
    """
    page = taranis_frontend
    base_url: str = e2e_server.url()

    cookies = _cookies_from_response(access_token_response)
    context_cookies = []
    context_cookies.extend(
        {
            "name": c["name"],
            "value": c["value"],
            "url": base_url,
        }
        for c in cookies
    )
    page.context.add_cookies(context_cookies)

    yield page


@pytest.fixture
def forward_console_and_page_errors(request, logged_in_page):
    """
    For each test:
      - collect console messages and page errors
      - at teardown: fail on configured severities, warn on warnings
    """
    page = logged_in_page
    fail_on = {x.strip() for x in request.config.getoption("--fail-on-console").split(",") if x.strip()}
    warn_on = {x.strip() for x in request.config.getoption("--warn-on-console").split(",") if x.strip()}
    allow_patterns = request.config.getoption("--console-allow") or []

    errors: list[str] = []
    warns: list[str] = []

    def on_console(msg):
        # types: "log", "debug", "info", "warning", "error", "trace", "timeEnd", "assert"
        t = (msg.type or "").lower()
        txt = msg.text
        loc = msg.location or {}
        loc_s = f"{loc.get('url', '')}:{loc.get('lineNumber', '?')}:{loc.get('columnNumber', '?')}"
        entry = f"[console.{t}] {loc_s} :: {txt}"

        if _allowed(txt, allow_patterns):
            return

        if t in fail_on:
            errors.append(entry)
        elif t in warn_on:
            warns.append(entry)

    def on_pageerror(err):
        entry = f"[pageerror] {err}"
        if _allowed(str(err), allow_patterns):
            return
        if "pageerror" in fail_on:
            errors.append(entry)
        elif "pageerror" in warn_on:
            warns.append(entry)

    page.on("console", on_console)
    page.on("pageerror", on_pageerror)

    try:
        yield
    finally:
        page.remove_listener("console", on_console)
        page.remove_listener("pageerror", on_pageerror)

        for w in warns:
            pywarnings.warn(UserWarning(w), stacklevel=0)

        if errors:
            bullet_list = "\n".join(f"  - {e}" for e in errors)
            pytest.fail(f"Console/Page errors detected:\n{bullet_list}")
