import contextlib
import os
import random
import re
import subprocess
import time
import warnings as pywarnings
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from urllib.parse import urlparse

import pytest
import requests
import responses
from dotenv import dotenv_values
from flask import json
from playwright.sync_api import Browser, Page

# Import fixtures to register them
from tests.playwright.fixtures.test_news_item_list import news_items_list  # noqa: F401
from tests.playwright.fixtures.test_story_list_enriched import story_list_enriched  # noqa: F401


def _wait_for_server_to_be_alive(url: str, timeout_seconds: int = 10, poll_interval: float = 0.5):
    pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")
    responses.add_passthru(pattern)

    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        try:
            response = requests.get(url, timeout=timeout_seconds)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            time.sleep(poll_interval)
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
        with contextlib.suppress(Exception):
            parsed_uri = urlparse(env.get("SQLALCHEMY_DATABASE_URI"))
            os.remove(f"{parsed_uri.path}")

        print(f"Starting Taranis Core on port {taranis_core_port}")
        process = subprocess.Popen(
            ["flask", "run", "--no-reload", "--port", taranis_core_port],
            cwd=core_path,
            env=env,
            # stdout=subprocess.PIPE,
            # stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        core_url = env.get("TARANIS_CORE_URL", f"http://127.0.0.1:{taranis_core_port}/api")
        print(f"Waiting for Taranis Core to be available at: {core_url}")
        _wait_for_server_to_be_alive(f"{core_url}/isalive", taranis_core_start_timeout)

        yield core_url

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


@pytest.fixture(scope="session")
def stories_date_descending_important(run_core, access_token):
    pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")
    responses.add_passthru(pattern)

    headers = {"Authorization": f"Bearer {access_token}"}

    story_ids = []
    stories = requests.get(f"{run_core}/assess/stories?important=true", headers=headers).json()
    for story in stories.get("items", []):
        story_ids.append(story.get("id"))
    yield story_ids


@pytest.fixture(scope="session")
def stories_relevance_descending(run_core, stories_date_descending, access_token):
    pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")
    responses.add_passthru(pattern)

    headers = {"Authorization": f"Bearer {access_token}"}
    stories_relevance_desc = requests.get(f"{run_core}/assess/stories?sort=relevance", headers=headers).json().get("items", [])
    yield [story.get("id") for story in stories_relevance_desc]


@pytest.fixture(scope="session")
def stories_date_descending(run_core, stories_session_wrapper, access_token):
    pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")
    responses.add_passthru(pattern)
    headers = {"Authorization": f"Bearer {access_token}"}

    story_ids = []
    s = requests.get(f"{run_core}/assess/stories", headers=headers).json()
    for story in s.get("items", []):
        story_ids.append(story.get("id"))

    assert len(story_ids) > 0, "No stories found for stories_date_descending fixture"

    yield story_ids


@pytest.fixture(scope="session")
def stories_date_descending_not_important(run_core, stories_session_wrapper, access_token):
    pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")
    responses.add_passthru(pattern)
    headers = {"Authorization": f"Bearer {access_token}"}
    story_ids = []
    s = requests.get(f"{run_core}/assess/stories?important=false&limit=50", headers=headers).json()
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
def stories_function_wrapper(run_core, api_header, fake_source, access_token):
    stories_list, request_responses = stories(run_core, api_header, fake_source, access_token)

    yield stories_list

    headers = {"Authorization": f"Bearer {access_token}"}
    news_item_ids_created = []
    for news_item_ids in request_responses:
        news_item_ids_created.extend(news_item_ids.json().get("news_item_ids"))
    for news_item_id in news_item_ids_created:
        requests.delete(f"{run_core}/assess/news-items/{news_item_id}", headers=headers)


@pytest.fixture(scope="session")
def stories_session_wrapper(run_core, api_header, fake_source, access_token):
    stories_list, _ = stories(run_core, api_header, fake_source, access_token)
    yield stories_list


def stories(run_core, api_header, fake_source, access_token):
    """
    Loads stories from test_stories.json, normalizes them to the structure
    defined in story_item_list (only keeping relevant keys and nested keys),
    and yields the cleaned list.
    """
    pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")
    responses.add_passthru(pattern)

    dir_path = os.path.dirname(os.path.realpath(__file__))
    story_json = os.path.join(dir_path, "test_stories.json")

    with open(story_json, encoding="utf-8") as f:
        stories_raw = json.load(f)

    def clean_news_item(item, story_id: str):
        """Keep only the same fields as in story_item_list fixture."""
        allowed_fields = {
            "id",
            "title",
            "content",
            "author",
            "source",
            "link",
            "language",
            # "osint_source_id",
            "review",
            "collected",
            "published",
            "story_id",
            "hash",
        }
        cleaned = {k: v for k, v in item.items() if k in allowed_fields}

        # Ensure required values are set
        cleaned.setdefault("language", None)
        cleaned["story_id"] = story_id
        cleaned["osint_source_id"] = fake_source
        return cleaned

    def clean_story(story):
        """Keep only whitelisted fields and clean nested news_items."""
        allowed_story_fields = {
            "id",
            "title",
            "description",
            "created",
            "read",
            "important",
            "likes",
            "dislikes",
            "relevance",
            "comments",
            "summary",
            "news_items",
            "tags",
            "attributes",
        }

        cleaned_story = {k: v for k, v in story.items() if k in allowed_story_fields}

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
        r = requests.post(f"{run_core}/worker/stories", json=story, headers=api_header)
        request_responses.append(r)

        # === Story grouping (clustering) logic ===
    story_groups = [
        [cleaned_stories[0]["id"], cleaned_stories[1]["id"]],
        [cleaned_stories[2]["id"], cleaned_stories[3]["id"]],
        [cleaned_stories[4]["id"], cleaned_stories[5]["id"]],
    ]

    headers = {"Authorization": f"Bearer {access_token}"}

    group_url = f"{run_core}/assess/stories/group"
    for group in story_groups:
        group_ids = [story_id for story_id in group]
        r = requests.put(group_url, json=group_ids, headers=headers)
        print(f"Grouped stories {group_ids} -> {r.status_code}")
        r.raise_for_status()

    result_stories = requests.get(f"{run_core}/worker/stories", headers=api_header).json()
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


@pytest.fixture(scope="session")
def pre_seed_stories(news_items_list, run_core, access_token):
    pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")
    responses.add_passthru(pattern)
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    print("Pre-seeding stories via assess API")
    for item in news_items_list:
        r = requests.post(f"{run_core}/assess/news-items", json=item, headers=headers)
        r.raise_for_status()

    yield []


@pytest.fixture(scope="session")
def pre_seed_stories_enriched(story_list_enriched, run_core, api_header):
    pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")
    responses.add_passthru(pattern)

    print("Pre-seeding stories via assess API")
    for story in story_list_enriched:
        r = requests.post(f"{run_core}/worker/stories", json=story, headers=api_header)
        r.raise_for_status()

    yield []


@pytest.fixture(scope="session")
def pre_seed_report_stories(story_item_list, run_core, api_header, access_token):
    pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")
    responses.add_passthru(pattern)

    print("Pre-seeding stories via worker API")

    for story in story_item_list:
        r = requests.post(f"{run_core}/worker/stories", json=story, headers=api_header)
        r.raise_for_status()

    yield story_item_list


@pytest.fixture(scope="session")
def test_osint_source():
    # get absoulute path to testdata/test_osint_source.json
    dir_path = os.path.dirname(os.path.realpath(__file__))
    yield os.path.join(dir_path, "testdata", "test_osint_source.json")


@pytest.fixture(scope="session")
def test_user():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    yield os.path.join(dir_path, "testdata", "test_users_to_import.json")


@pytest.fixture(scope="session")
def test_user_list():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    yield os.path.join(dir_path, "testdata", "test_users_list.json")


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
def fake_source(app, run_core, access_token):
    pattern = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")
    responses.add_passthru(pattern)

    source_data = {
        "id": "99",
        "description": "This is a test source",
        "name": "Test Source",
        "parameters": [
            {"FEED_URL": "https://url/feed.xml"},
        ],
        "type": "rss_collector",
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    r = requests.post(f"{run_core}/config/osint-sources", json=source_data, headers=headers)
    r.raise_for_status()

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
                    "id": "4b9a5a9e-04d7-41fc-928f-99e5ad608ebq",
                    "story_id": "78049551-dcef-45bd-a5cd-4fe842c4d5e3",
                    "hash": "a96e88baaff421165e90ac4bb9059971b86f88d5c2abba36d78a1264fb8e9c82",
                    "title": "Test News Item 13",
                    "content": "Microsoft announced a security update addressing CVE-2020-1234. Experts at Google found vulnerabilities impacting Linux systems. Cisco advises users to update their security protocols to prevent potential breaches. The security community is on alert for new threats.",
                    "collected": "2023-08-01T17:01:04.802015",
                    "published": "2023-08-01T17:01:04.801998",
                }
            ],
            # "tags": {
            #     "this": {"name": "this", "tag_type": "misc"},
            #     "is": {"name": "is", "tag_type": "misc"},
            #     "tag": {"name": "tag", "tag_type": "misc"},
            # },
            # "attributes": {
            #     "attribute": {"key": "attribute", "value": "custom"},
            #     "hip": {"key": "hip", "value": "hop"},
            #     "cloth": {"key": "cloth", "attribute_type": "short"},
            # },
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
            "comments": "",
            "summary": "",
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
            # "tags": [{"name": "test", "tag_type": "misc"}, {"name": "story", "tag_type": "misc"}, {"name": "news", "tag_type": "misc"}],
            # "attributes": [
            #     {"key": "severity", "value": "high"},
            #     {"key": "impact", "value": "critical"},
            #     {"key": "status", "value": "investigating"},
            # ],
        },
    ]
