import base64
import copy
import multiprocessing
import os
import random
import re
import subprocess
import warnings as pywarnings
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any

import pytest
import responses
from flask import json, url_for
from models.user import USER_PRODUCT_OVERVIEW_TASK_ID
from playwright.sync_api import Browser, BrowserContext, Page, expect

from tests.core_requests import CoreRequestClient
from tests.external_e2e import (
    LOCALHOST_PASSTHRU_PATTERN,
    allow_requests_passthru,
    core_host_from_api_url,
    external_auth_credentials,
    external_basic_auth_credentials,
    external_core_api_url,
    external_frontend_base_url,
    login_to_core,
    wait_for_server_to_be_alive,
)
from tests.playwright.e2e_harness import (
    docker_cleanup_commands,
    docker_setup_commands,
    require_docker_compose_command,
)
from tests.playwright.fixtures.test_news_item_list import news_items_list  # noqa: F401
from tests.playwright.fixtures.test_story_list_enriched import story_list_enriched  # noqa: F401
from tests.playwright.htmx_helpers import install_htmx_support
from tests.playwright.notification_helpers import dismiss_notifications


def _configure_live_server_start_method() -> None:
    if "fork" not in multiprocessing.get_all_start_methods():
        return

    current_method = multiprocessing.get_start_method(allow_none=True)
    if current_method is None:
        multiprocessing.set_start_method("fork")


_configure_live_server_start_method()


FRONTEND_E2E_COMPOSE_FILE = Path(__file__).parent / "compose.e2e.yml"


class ExternalE2EServer:
    def __init__(self, base_url: str):
        self._base_url = base_url

    def url(self) -> str:
        return self._base_url


def _core_token_response(user_type: str, access_token_response, access_token_response_basic):
    if user_type == "admin":
        return access_token_response
    if user_type == "basic":
        return access_token_response_basic
    raise ValueError(f"Unknown user_type: {user_type}")


def _external_token_response(user_type: str):
    core_api_url = external_core_api_url()
    if core_api_url is None:
        raise RuntimeError("External core URL is not configured")

    if user_type == "admin":
        username, password = external_auth_credentials()
    elif user_type == "basic":
        username, password = external_basic_auth_credentials()
    else:
        raise ValueError(f"Unknown user_type: {user_type}")

    return login_to_core(core_api_url, username, password)


@pytest.fixture(scope="session")
def docker_compose_file():
    return str(FRONTEND_E2E_COMPOSE_FILE)


@pytest.fixture(scope="session")
def docker_compose_command() -> str:
    return require_docker_compose_command()


@pytest.fixture(scope="session")
def docker_setup(docker_compose_command):
    return docker_setup_commands(docker_compose_command)


@pytest.fixture(scope="session")
def docker_cleanup():
    return docker_cleanup_commands()


@pytest.fixture(scope="session")
def run_core_external():
    from frontend.config import Config

    taranis_core_start_timeout = int(os.getenv("TARANIS_CORE_START_TIMEOUT", 120))
    external_core_url = external_core_api_url()
    if external_core_url is None:
        raise RuntimeError("External core URL is not configured")

    Config.TARANIS_CORE_HOST = core_host_from_api_url(external_core_url)
    Config.TARANIS_CORE_URL = external_core_url
    print(f"Using external Taranis Core for E2E tests: {external_core_url}")
    wait_for_server_to_be_alive(f"{external_core_url}/health", taranis_core_start_timeout)
    return external_core_url


@pytest.fixture(scope="session")
def run_core_local(docker_services):
    from frontend.config import Config

    taranis_core_start_timeout = int(os.getenv("TARANIS_CORE_START_TIMEOUT", 120))
    core_port = docker_services.port_for("core", 8080)
    core_url = f"http://127.0.0.1:{core_port}/api"

    Config.TARANIS_CORE_HOST = f"http://127.0.0.1:{core_port}"
    Config.TARANIS_CORE_URL = core_url

    try:
        print("Starting Taranis Core Docker service for E2E tests (pytest-docker)")
        print(f"Waiting for Taranis Core to be available at: {core_url}")
        wait_for_server_to_be_alive(f"{core_url}/health", taranis_core_start_timeout)
        return core_url
    except Exception as e:
        pytest.fail(str(e))


@pytest.fixture(scope="session")
def run_core(request):
    if external_core_api_url():
        return request.getfixturevalue("run_core_external")
    return request.getfixturevalue("run_core_local")


@pytest.fixture(scope="session")
def build_tailwindcss(app):
    def assets_need_rebuild() -> bool:
        vendor_bundle = Path("frontend/static/vendor/vendor.bundle.js")
        vendor_css = Path("frontend/static/vendor/vendor.bundle.css")
        return (
            os.getenv("TARANIS_E2E_TEST_TAILWIND_REBUILD") == "true"
            or not os.path.isfile("frontend/static/css/tailwind.css")
            or not vendor_bundle.is_file()
            or not vendor_css.is_file()
        )

    try:
        if assets_need_rebuild():
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


@pytest.fixture(scope="session", autouse=True)
def e2e_requests_mock():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add_passthru(LOCALHOST_PASSTHRU_PATTERN)
        yield rsps


@pytest.fixture(scope="function", autouse=True)
def allow_localhost_core_requests(e2e_requests_mock) -> None:
    e2e_requests_mock.add_passthru(LOCALHOST_PASSTHRU_PATTERN)


@pytest.fixture(scope="session")
def e2e_server_external():
    external_frontend_url = external_frontend_base_url()
    if external_frontend_url is None:
        raise RuntimeError("External frontend URL is not configured")
    print(f"Using external Taranis Frontend for E2E tests: {external_frontend_url}")
    return ExternalE2EServer(external_frontend_url)


@pytest.fixture(scope="session")
def e2e_server_local(run_core, app, live_server, build_tailwindcss):
    live_server.app = app
    live_server.start()
    return live_server


@pytest.fixture(scope="session")
def e2e_server(request):
    if external_frontend_base_url():
        return request.getfixturevalue("e2e_server_external")
    return request.getfixturevalue("e2e_server_local")


@pytest.fixture(scope="function")
def e2e_request_context(e2e_server, app):
    app = getattr(e2e_server, "app", None) or app
    with app.test_request_context():
        yield


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, browser_type_launch_args, request):
    browser_type_launch_args["args"] = ["--window-size=1964,1211"]

    if request.config.getoption("--record-video"):
        browser_type_launch_args["args"] = ["--window-size=1964,1211"]
        print("Screenshots in --record-video mode are not of optimal resolution")
        return {
            **browser_context_args,
            "record_video_dir": "tests/playwright/videos",
            "no_viewport": True,
            "record_video_size": {"width": 1920, "height": 1080},
        }
    return {**browser_context_args, "no_viewport": True}


@pytest.fixture(scope="session")
def setup_test_templates(core_request_client):
    """Set up test template files for e2e tests via core API."""
    test_data_dir = Path(__file__).parent / "testdata"

    uploaded_templates = []
    for test_file in test_data_dir.glob("*.html"):
        payload = {
            "id": test_file.name,
            "content": base64.b64encode(test_file.read_bytes()).decode("utf-8"),
        }
        core_request_client.post("/config/templates", json_data=payload, timeout_seconds=30)
        uploaded_templates.append(test_file.name)

    yield

    for template_name in uploaded_templates:
        try:
            core_request_client.delete(f"/config/templates/{template_name}", timeout_seconds=30)
        except Exception:
            pass


@pytest.fixture(scope="function")
def taranis_frontend(request, e2e_request_context, setup_test_templates, browser_context_args, browser: Browser):
    timeout = int(request.config.getoption("--e2e-timeout"))
    expect.set_options(timeout=timeout)
    context = browser.new_context(**browser_context_args)
    install_htmx_support(context)
    context.set_default_timeout(timeout)
    if request.config.getoption("trace"):
        context.tracing.start(screenshots=True, snapshots=True, sources=True)

    page = context.new_page()
    try:
        yield page
    finally:
        if request.config.getoption("trace"):
            context.tracing.stop(path="taranis_ai_frontend_trace.zip")
        page.close()
        context.close()


def _allowed(entry: str, allow_patterns: list[str]) -> bool:
    return any(re.search(pattern, entry) for pattern in allow_patterns)


def _dismiss_notifications(page: Page):
    dismiss_notifications(page)


def _cookies_from_response(resp) -> list[dict]:
    """Parse Flask Response `Set-Cookie` headers into Playwright cookie dicts (name/value/path only)."""
    if getattr(resp, "cookies", None):
        return [{"name": name, "value": value} for name, value in resp.cookies.items()]

    cookies: list[dict] = []
    for header in resp.headers.getlist("Set-Cookie"):
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


def _add_auth_cookies(context: BrowserContext, base_url: str, token_response) -> None:
    cookies = _cookies_from_response(token_response)
    context_cookies = []
    context_cookies.extend(
        {
            "name": c["name"],
            "value": c["value"],
            "url": base_url,
        }
        for c in cookies
    )
    context.add_cookies(context_cookies)


def _new_authenticated_page(taranis_frontend: Page, e2e_server, token_response) -> Page:
    context = taranis_frontend.context
    base_url: str = e2e_server.url()

    # Ensure we do not leak auth state across test segments (admin -> user).
    context.clear_cookies()
    _add_auth_cookies(context, base_url, token_response)

    page = context.new_page()
    _dismiss_notifications(page)
    return page


@pytest.fixture
def authenticated_page_factory_local(taranis_frontend: Page, e2e_server, access_token_response, access_token_response_basic):
    """Factory fixture for creating authenticated pages with different user types."""

    def _create(user_type="admin"):
        token_response = _core_token_response(user_type, access_token_response, access_token_response_basic)
        return _new_authenticated_page(taranis_frontend, e2e_server, token_response)

    return _create


def complete_user_product_overview_task(core_url: str, access_token: str):
    allow_requests_passthru(core_url)
    response = CoreRequestClient(base_url=core_url, access_token=access_token).post(
        "/users/profile",
        json_data={"onboarding_tasks": {USER_PRODUCT_OVERVIEW_TASK_ID: "completed"}},
    )
    assert response.ok, f"Failed to complete user onboarding task: {response.status_code}"


@pytest.fixture
def authenticated_page_factory_external(taranis_frontend: Page, e2e_server):
    """Factory fixture for creating authenticated pages against an external core."""

    def _create(user_type="admin"):
        token_response = _external_token_response(user_type)
        return _new_authenticated_page(taranis_frontend, e2e_server, token_response)

    return _create


@pytest.fixture
def authenticated_page_factory(request):
    if external_core_api_url():
        return request.getfixturevalue("authenticated_page_factory_external")
    return request.getfixturevalue("authenticated_page_factory_local")


@pytest.fixture
def logged_in_page(authenticated_page_factory):
    """Returns a Playwright Page with admin authentication."""
    page = authenticated_page_factory("admin")
    try:
        yield page
    finally:
        _dismiss_notifications(page)
        page.close()


def _token_from_response(token_response) -> str:
    access_token = token_response.json().get("access_token")
    if not access_token:
        raise RuntimeError("Login response does not contain 'access_token'")
    return access_token


@pytest.fixture
def non_admin_logged_in_page(request, authenticated_page_factory, run_core):
    """Returns a Playwright Page with basic user authentication."""
    access_token = (
        _token_from_response(_external_token_response("basic")) if external_core_api_url() else request.getfixturevalue("access_token_basic")
    )
    complete_user_product_overview_task(run_core, access_token)
    page = authenticated_page_factory("basic")
    try:
        yield page
    finally:
        _dismiss_notifications(page)
        page.close()


@pytest.fixture
def ensure_basic_user_permissions(non_admin_logged_in_page):
    """Fail fast when a user suite accidentally runs with admin privileges."""
    page = non_admin_logged_in_page

    page.goto(url_for("base.dashboard", _external=True))
    assert page.get_by_role("link", name="Administration").count() == 0, "Basic user unexpectedly sees Administration menu"

    page.goto(url_for("admin.attributes", _external=True))
    expect(page.get_by_text("403 - Access denied")).to_be_visible()


def _forward_console_and_page_errors(request, page: Page, extra_allow_patterns: list[str] | None = None):
    fail_on = {x.strip() for x in request.config.getoption("--fail-on-console").split(",") if x.strip()}
    warn_on = {x.strip() for x in request.config.getoption("--warn-on-console").split(",") if x.strip()}
    allow_patterns = [
        *(request.config.getoption("--console-allow") or []),
        *(extra_allow_patterns or []),
    ]

    errors: list[str] = []
    warns: list[str] = []

    def on_console(msg):
        # types: "log", "debug", "info", "warning", "error", "trace", "timeEnd", "assert"
        t = (msg.type or "").lower()
        txt = msg.text
        loc = msg.location or {}
        loc_s = f"{loc.get('url', '')}:{loc.get('lineNumber', '?')}:{loc.get('columnNumber', '?')}"
        entry = f"[console.{t}] {loc_s} :: {txt}"

        if _allowed(entry, allow_patterns):
            return

        if t in fail_on:
            errors.append(entry)
        elif t in warn_on:
            warns.append(entry)

    def on_pageerror(err):
        entry = f"[pageerror] {err}"
        if _allowed(entry, allow_patterns):
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
        _dismiss_notifications(page)

        for w in warns:
            pywarnings.warn(UserWarning(w), stacklevel=0)

        if errors:
            bullet_list = "\n".join(f"  - {e}" for e in errors)
            pytest.fail(f"Console/Page errors detected:\n{bullet_list}")


@pytest.fixture
def forward_console_and_page_errors(request, logged_in_page):
    """
    For each test:
      - collect console messages and page errors
      - at teardown: fail on configured severities, warn on warnings
    """
    yield from _forward_console_and_page_errors(request, logged_in_page)


@pytest.fixture
def forward_console_and_page_errors_non_admin(request, non_admin_logged_in_page):
    yield from _forward_console_and_page_errors(
        request,
        non_admin_logged_in_page,
        extra_allow_patterns=[
            r"(?i)\[console\.error\].*/admin/attributes.*Failed to load resource: the server responded with a status of 403 \(forbidden\)",
            r"\[console\.error\].*htmx:oobErrorNoTarget, #notification-bar",
        ],
    )


@pytest.fixture
def forward_console_and_page_errors_non_admin_report_forbidden(request, non_admin_logged_in_page):
    yield from _forward_console_and_page_errors(
        request,
        non_admin_logged_in_page,
        extra_allow_patterns=[
            r"(?i)\[console\.error\].*/report/.*Failed to load resource: the server responded with a status of 403 \(forbidden\)",
        ],
    )


@pytest.fixture(scope="session")
def stories_date_descending_important(core_request_client):
    allow_requests_passthru()

    story_ids = []
    stories = core_request_client.json_request("GET", "/assess/stories", params={"important": "true"})
    for story in stories.get("items", []):
        story_ids.append(story.get("id"))
    yield story_ids


@pytest.fixture(scope="session")
def stories_relevance_descending(core_request_client, stories_date_descending):
    allow_requests_passthru()

    stories_relevance_desc = core_request_client.json_request("GET", "/assess/stories", params={"sort": "relevance"}).get("items", [])
    yield [story.get("id") for story in stories_relevance_desc]


@pytest.fixture(scope="session")
def stories_date_descending(core_request_client, stories_session_wrapper):
    allow_requests_passthru()

    story_ids = []
    s = core_request_client.json_request("GET", "/assess/stories")
    for story in s.get("items", []):
        story_ids.append(story.get("id"))

    assert len(story_ids) > 0, "No stories found for stories_date_descending fixture"

    yield story_ids


@pytest.fixture(scope="session")
def stories_date_descending_not_important(core_request_client, stories_session_wrapper):
    allow_requests_passthru()
    story_ids = []
    s = core_request_client.json_request("GET", "/assess/stories", params={"important": "false", "limit": 50})
    for story in s.get("items"):
        story_ids.append(story.get("id"))
    yield story_ids


def random_timestamp_last_5_days() -> str:
    now = datetime.now()
    start_time = now - timedelta(days=5)
    return (start_time + timedelta(seconds=random.randint(0, int((now - start_time).total_seconds())))).isoformat()


def random_timestamp_last_shift() -> str:
    ### Add a random timestamp between now and yesterday 18:00
    now = datetime.now()
    start_time = now - timedelta(days=1)
    start_time = start_time.replace(hour=18, minute=0, second=0, microsecond=0)
    return (start_time + timedelta(seconds=random.randint(0, int((now - start_time).total_seconds())))).isoformat()


@pytest.fixture(scope="function")
def stories_function_wrapper(api_header, fake_source, core_request_client):
    stories_list, request_responses = stories(core_request_client, api_header, fake_source)

    yield stories_list

    news_item_ids_created = []
    for news_item_ids in request_responses:
        try:
            news_item_ids_created.extend(news_item_ids.json().get("news_item_ids", []))
        except Exception:
            continue
    for news_item_id in news_item_ids_created:
        try:
            core_request_client.delete(f"/assess/news-items/{news_item_id}")
        except Exception:
            pass


@pytest.fixture(scope="session")
def stories_session_wrapper(api_header, fake_source, core_request_client):
    stories_list, _ = stories(core_request_client, api_header, fake_source)
    yield stories_list


def stories(core_request_client, api_header, fake_source):
    """
    Loads stories from test_stories.json, normalizes them to the structure
    defined in story_item_list (only keeping relevant keys and nested keys),
    and yields the cleaned list.
    """
    allow_requests_passthru()

    dir_path = os.path.dirname(os.path.realpath(__file__))
    story_json = os.path.join(dir_path, "test_stories.json")

    with open(story_json, encoding="utf-8") as f:
        stories_raw = json.load(f)

    def clean_news_item(item: dict[str, Any], story_id: str):
        item.setdefault("language", None)
        item["story_id"] = story_id
        item["osint_source_id"] = fake_source
        return item

    def clean_story(story):
        cleaned_story = {k: v for k, v in story.items()}

        # Make sure all required top-level keys exist
        cleaned_story.setdefault("description", "")
        cleaned_story.setdefault("comments", "")
        cleaned_story.setdefault("summary", "")
        cleaned_story.setdefault("read", False)
        cleaned_story.setdefault("important", False)
        cleaned_story.setdefault("likes", 0)
        cleaned_story.setdefault("dislikes", 0)
        cleaned_story.setdefault("relevance", 0)

        # Clean news_items list
        news_items = story.get("news_items", [])
        cleaned_story["news_items"] = [clean_news_item(item, story["id"]) for item in news_items]

        return cleaned_story

    cleaned_stories = [clean_story(s) for s in stories_raw]

    # === Timestamp and importance logic ===
    def _renew_story_timestamps():
        # Randomize published/collected timestamps across stories
        for idx, story in enumerate(cleaned_stories):
            for item in story["news_items"]:
                if idx < len(cleaned_stories) - 5:
                    new_time = random_timestamp_last_shift()
                else:
                    new_time = random_timestamp_last_5_days()
                item.update({"published": new_time, "collected": new_time})

    def _set_important_flags():
        important_indices = [0, 8, 13, 17, 21]
        for idx in important_indices:
            if idx < len(cleaned_stories):
                cleaned_stories[idx]["important"] = True

    _renew_story_timestamps()
    _set_important_flags()
    request_responses = []
    for story in cleaned_stories[:36]:
        r = core_request_client.post(
            "/worker/stories",
            json_data=story,
            headers=api_header,
            authenticated=False,
            raise_for_status=False,
        )
        request_responses.append(r)
        if r.status_code == 409:
            continue
        r.raise_for_status()

        # === Story grouping (clustering) logic ===
    story_groups = [
        [cleaned_stories[0]["id"], cleaned_stories[1]["id"]],
        [cleaned_stories[2]["id"], cleaned_stories[3]["id"]],
        [cleaned_stories[4]["id"], cleaned_stories[5]["id"]],
    ]

    for group in story_groups:
        group_ids = [story_id for story_id in group]
        r = core_request_client.put("/assess/stories/group", json_data=group_ids)
        print(f"Grouped stories {group_ids} -> {r.status_code}")

    result_stories = core_request_client.json_request("GET", "/worker/stories", headers=api_header, authenticated=False)
    return result_stories, request_responses


# @pytest.fixture(scope="session")
# def create_html_render(app):
#     # fixture returns a callable, so that we can choose the time to execute it
#     def get_product_to_render(timeout=5.0, interval=1.0):
#         with app.app_context():
#             import time
#             from core.model.product import Product
#             from core.managers.db_manager import db

#             # get id of first product in product table
#             start_time = time.time()
#             product = None

#             while time.time() - start_time < timeout:
#                 product = Product.get_first(db.select(Product))
#                 if product:
#                     break
#                 time.sleep(interval)
#             else:
#                 raise RuntimeError("No products found in database")

#             # test html for product rendering
#             test_html_b64 = "VGhhbmtzIHRvIEN5YmVyc2VjdXJpdHkgZXhwZXJ0cywgdGhlIHdvcmxkIG9mIElUIGlzIG5vdyBzYWZlLg=="

#             _, status_code = Product.update_render_for_id(product.id, test_html_b64)

#             if status_code != 200:
#                 raise RuntimeError(f"Failed to render product with id {product.id}")

#     return get_product_to_render


@pytest.fixture(scope="module")
def pre_seed_stories(news_items_list, core_request_client):  # noqa: F811
    allow_requests_passthru()

    print("Pre-seeding stories via assess API")
    story_list = []
    news_item_ids_created: list[str] = []

    def _collect_story_news_item_ids(story_id: str) -> list[str]:
        try:
            story = core_request_client.get(f"/assess/stories/{story_id}").json()
        except Exception:
            return []
        news_items = story.get("news_items", []) if isinstance(story, dict) else []
        return [news_item.get("id") for news_item in news_items if isinstance(news_item, dict) and news_item.get("id")]

    for item in news_items_list:
        r = core_request_client.post("/assess/news-items", json_data=item, raise_for_status=False)
        if not r.ok:
            if r.status_code == 409:
                payload = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                skipped_story_id = payload.get("skipped_news_item_story_id")
                if isinstance(skipped_story_id, str):
                    story_list.append({"story_id": skipped_story_id, **item})
                    news_item_ids_created.extend(_collect_story_news_item_ids(skipped_story_id))
                    continue
            try:
                error_payload = r.json()
            except ValueError:
                error_payload = r.text
            raise AssertionError(
                f"Failed to pre-seed news item '{item.get('title', '<unknown>')}' with status {r.status_code}: {error_payload}"
            )
        response_data = r.json()
        story_list.append({"story_id": response_data.get("story_id"), **item})
        news_item_ids_created.extend(response_data.get("news_item_ids", []))

    yield story_list

    for news_item_id in news_item_ids_created:
        try:
            core_request_client.delete(f"/assess/news-items/{news_item_id}")
        except Exception:
            pass


@pytest.fixture(scope="session")
def pre_seed_stories_enriched(story_list_enriched, api_header, core_request_client):  # noqa: F811
    allow_requests_passthru()

    print("Pre-seeding stories via assess API")
    for story in story_list_enriched:
        core_request_client.post("/worker/stories", json_data=story, headers=api_header, authenticated=False)

    yield []


@pytest.fixture(scope="session")
def pre_seed_report_stories(story_item_list, api_header, core_request_client):
    allow_requests_passthru()

    print("Pre-seeding stories via worker API")

    for story in story_item_list:
        core_request_client.post("/worker/stories", json_data=story, headers=api_header, authenticated=False)

    yield story_item_list


ALL_ATTRIBUTE_TYPES = {
    "STRING",
    "NUMBER",
    "BOOLEAN",
    "RADIO",
    "ENUM",
    "TEXT",
    "RICH_TEXT",
    "DATE",
    "TIME",
    "DATE_TIME",
    "LINK",
    "ATTACHMENT",
    "TLP",
    "CPE",
    "CVE",
    "CVSS",
    "STORY",
}


def pre_seed_report_type(report_definition, core_request_client):
    allow_requests_passthru()

    r = core_request_client.get("/config/attributes", params={"limit": 300})
    items = r.json()["items"]

    # Build lookups
    by_name = {a["name"]: a for a in items}
    available_types = {a["type"] for a in items if "type" in a}

    # Assert: the report covers all AttributeTypes present in the system
    referenced_names = [item["attribute"] for g in report_definition["attribute_groups"] for item in g["attribute_group_items"]]
    referenced_types = {by_name[name]["type"] for name in referenced_names}
    missing_types = sorted(available_types - referenced_types)
    assert not missing_types, (
        f"Report does not cover all AttributeTypes present in the system. Missing: {missing_types}. Covered: {sorted(referenced_types)}"
    )

    # Assert: system has no unexpected AttributeTypes (i.e., new types were added)
    unexpected_types = sorted(available_types - ALL_ATTRIBUTE_TYPES)
    assert not unexpected_types, f"System has unexpected AttributeTypes: {unexpected_types}"

    core_request_client.post("/config/report-item-types", json_data=report_definition)


@pytest.fixture(scope="session")
def pre_seed_report_type_all_attribute_types_optional(core_request_client):
    from testdata.report_item_type_all_attribute_types import report_definition

    report_definition_copy = copy.deepcopy(report_definition)
    pre_seed_report_type(report_definition_copy, core_request_client)


@pytest.fixture(scope="session")
def pre_seed_report_type_all_attribute_types_required(core_request_client):
    from testdata.report_item_type_all_attribute_types import report_definition

    report_definition_copy = copy.deepcopy(report_definition)
    report_definition_copy["title"] = report_definition_copy.get("title", "") + " REQUIRED"

    for attribute_group in report_definition_copy.get("attribute_groups", {}):
        for attribute in attribute_group.get("attribute_group_items", {}):
            attribute["required"] = True

    pre_seed_report_type(report_definition_copy, core_request_client)


@pytest.fixture(scope="session")
def testdata_dir():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    yield os.path.join(dir_path, "testdata")


@pytest.fixture(scope="session")
def test_osint_source(testdata_dir):
    yield os.path.join(testdata_dir, "test_osint_source.json")


@pytest.fixture
def test_osint_icon_png(testdata_dir):
    yield os.path.join(testdata_dir, "icon.png")


@pytest.fixture
def test_batch_osint_sources(core_request_client, e2e_server, access_token_response, testdata_dir):

    def invalidate_osint_source_caches() -> None:
        core_request_client.post("/admin/cache/invalidate", json_data={"mode": "all"}, timeout_seconds=30)

    allow_requests_passthru()

    with open(os.path.join(testdata_dir, "test_report_item_type_sources_paging.json"), encoding="utf-8") as f:
        source_data = json.load(f)

        core_request_client.post("/config/import-osint-sources", json_data=source_data)
        invalidate_osint_source_caches()

    yield source_data

    try:
        list_response = core_request_client.get("/config/osint-sources")
        for source in list_response.json().get("items", []):
            if source_id := source.get("id"):
                try:
                    core_request_client.delete(
                        f"/config/osint-sources/{source_id}",
                        params={"force": "true"},
                    )
                except Exception:
                    pass
    except Exception:
        pass
    invalidate_osint_source_caches()


@pytest.fixture(scope="session")
def test_user(testdata_dir):
    yield os.path.join(testdata_dir, "test_users_to_import.json")


@pytest.fixture(scope="session")
def test_user_list(testdata_dir):
    yield os.path.join(testdata_dir, "test_users_list.json")


@pytest.fixture(scope="session")
def test_wordlist(testdata_dir):
    yield os.path.join(testdata_dir, "test_word_list.json")


def report_item_dict(story_item_list):
    yield {
        "title": "Weekly APT Activity Report",
        "report_item_type_id": 1,
        "completed": False,
        "stories": [story_item_list[0]["id"], story_item_list[1]["id"]],
        "attributes": [
            {
                "title": "Report Classification",
                "description": "TLP level of this report",
                "value": "TLP:GREEN",
                "index": 0,
                "required": True,
                "attribute_type": "TLP",
                "group_title": "Metadata",
                "render_data": {},
            },
            {
                "title": "Summary",
                "description": "High-level overview of observed APT activities",
                "value": "Includes analysis of APT82–85 targeting critical infrastructure.",
                "index": 1,
                "required": False,
                "attribute_type": "TEXT",
                "group_title": "Metadata",
                "render_data": {},
            },
        ],
    }


@pytest.fixture(scope="session")
def fake_source(core_request_client):
    allow_requests_passthru()

    source_data = {
        "id": "019b678a-3c63-736a-8c81-59c737fc4f53",
        "description": "This is a test source",
        "name": "Test Source",
        "parameters": {"FEED_URL": "https://url/feed.xml"},
        "type": "rss_collector",
    }

    core_request_client.post("/config/osint-sources", json_data=source_data)

    yield source_data["id"]


@pytest.fixture(scope="session")
def story_item_list(fake_source):
    yield [
        {
            "id": "78049551-dcef-45bd-a5cd-4fe842c4d5e3",
            "title": "Report Story 1",
            "description": "Test Aggregate",
            "created": "2023-08-01T17:01:04.801870",
            "read": False,
            "important": False,
            "likes": 0,
            "dislikes": 0,
            "relevance": 0,
            "comments": "",
            "summary": "",
            "news_items": [
                {
                    "review": "",
                    "author": "James Bond",
                    "source": "https://url/",
                    "link": "https://url/",
                    "language": None,
                    "osint_source_id": fake_source,
                    "id": "4b9a5a9e-04d7-41fc-928f-99e5ad608eba",
                    "story_id": "78049551-dcef-45bd-a5cd-4fe842c4d5e3",
                    "hash": "a96e88baaff421165e90ac4bb9059971b86f88d5c2abba36d78a1264fb8e9c82",
                    "title": "Test News Item 13",
                    "content": "Microsoft announced a security update addressing CVE-2020-1234. Experts at Google found vulnerabilities impacting Linux systems. Cisco advises users to update their security protocols to prevent potential breaches. The security community is on alert for new threats.",
                    "collected": "2023-08-01T17:01:04.802015",
                    "published": "2023-08-01T17:01:04.801998",
                }
            ],
            "tags": {
                "this": {"name": "this", "tag_type": "misc"},
                "is": {"name": "is", "tag_type": "misc"},
                "tag": {"name": "tag", "tag_type": "misc"},
            },
            "attributes": {
                "attribute": {"key": "attribute", "value": "custom"},
                "hip": {"key": "hip", "value": "hop"},
                "cloth": {"key": "cloth", "attribute_type": "short"},
            },
        },
        {
            "id": "f2bbda19-c353-4ea4-922c-388c5ce80172",
            "title": "Report Story 2",
            "description": "Synthetic story for testing: includes two news items under the same story.",
            "created": "2024-07-12T20:12:00.123456",
            "read": False,
            "important": False,
            "likes": 0,
            "dislikes": 0,
            "relevance": 0,
            "comments": "test comment",
            "summary": "test summary",
            "news_items": [
                {
                    "review": "",
                    "author": "",
                    "source": "https://securitynews.example.com/item1",
                    "link": "https://securitynews.example.com/item1",
                    "language": None,
                    "osint_source_id": fake_source,
                    "id": "90f0d9ec-70e7-45cf-8919-6ae2c02a4d88",
                    "story_id": "f2bbda19-c353-4ea4-922c-388c5ce80172",
                    "hash": "3e6f7ef83f93d7a5145d72c7a9b9d37b9d229c0b97c1374eaa70b1ba46fc8342",
                    "title": "Zero-Day Vulnerability Exposed",
                    "content": "A previously unknown zero-day vulnerability was discovered in a major enterprise software platform. Security experts recommend immediate mitigation. Details remain limited as investigation continues.",
                    "collected": "2024-07-12T20:12:01.100000",
                    "published": "2024-07-12T19:45:00.000000",
                },
                {
                    "review": "",
                    "author": "",
                    "source": "https://securitynews.example.com/item2",
                    "link": "https://securitynews.example.com/item2",
                    "language": None,
                    "osint_source_id": fake_source,
                    "id": "c2a1c55c-6e7e-41de-8ad1-bda321f2f56b",
                    "story_id": "f2bbda19-c353-4ea4-922c-388c5ce80172",
                    "hash": "bd87e1b6f17314abfdc185af24f1d6385f0fd13b59d2e2193e3197f94c671a99",
                    "title": "Mitigation Steps Released for New Exploit",
                    "content": "Vendors have released official mitigation guidance in response to the recent zero-day exploit. Organizations are urged to apply the latest patches and review their security posture.",
                    "collected": "2024-07-12T20:12:01.200000",
                    "published": "2024-07-12T20:00:00.000000",
                },
            ],
            "tags": [{"name": "test", "tag_type": "misc"}, {"name": "story", "tag_type": "misc"}, {"name": "news", "tag_type": "misc"}],
            "attributes": [
                {"key": "severity", "value": "high"},
                {"key": "impact", "value": "critical"},
                {"key": "status", "value": "investigating"},
            ],
        },
    ]
