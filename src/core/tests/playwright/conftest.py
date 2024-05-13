import pytest
import subprocess
from playwright.sync_api import Browser


@pytest.fixture(scope="session")
def build_gui():
    yield subprocess.call(["npm", "run", "build"], cwd="../gui")


@pytest.fixture(scope="class")
def e2e_ci(build_gui, request):
    request.cls.ci_run = request.config.getoption("--run-e2e-ci") == "e2e_ci"
    request.cls.wait_duration = int(request.config.getoption("--highlight-delay"))
    request.cls.produce_artifacts = request.config.getoption("--produce-artifacts")


# Optional add build_gui
@pytest.fixture(scope="session")
def e2e_server(app, live_server, stories):
    import core.api as core_api

    core_api.frontend.initialize(app)
    live_server.app = app
    live_server.start()
    yield live_server


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, request):
    if request.config.getoption("--produce-artifacts"):
        return {**browser_context_args, "record_video_dir": "tests/playwright/videos", "viewport": {"width": 1920, "height": 1080}}
    return {**browser_context_args, "viewport": {"width": 1920, "height": 1080}}


@pytest.fixture(scope="session")
def taranis_frontend(e2e_server, browser_context_args, browser: Browser):
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    page.goto(e2e_server.url())
    yield page


@pytest.fixture(scope="session")
def fake_source(app):
    with app.app_context():
        from core.model.osint_source import OSINTSource

        source_data = {
            "id": "99",
            "description": "This is a test source",
            "name": "Test Source",
            "parameters": [
                {"FEED_URL": "https://url/feed.xml"},
            ],
            "type": "rss_collector",
        }
        OSINTSource.add(source_data)

        yield source_data["id"]


@pytest.fixture(scope="session")
def stories(app, fake_source):
    with app.app_context():
        from core.model.story import Story

        news_items_list = [
            {
                "id": "1be00eef-6ade-4818-acfc-25029531a9a5",
                "content": "TEST CONTENT YYYY",
                "source": "https: //www.some.link/RSSNewsfeed.xml",
                "title": "Mobile World Congress 2023",
                "author": "",
                "collected": "2022-02-21T15:00:14.086285",
                "hash": "82e6e99403686a1072d0fb2013901b843a6725ba8ac4266270f62b7614ec1adf",
                "review": "",
                "link": "https://www.some.other.link/2023.html",
                "osint_source_id": fake_source,
                "published": "2022-02-21T15:01:14.086285",
            },
            {
                "id": "0a129597-592d-45cb-9a80-3218108b29a0",
                "content": "TEST CONTENT XXXX",
                "source": "https: //www.content.xxxx.link/RSSNewsfeed.xml",
                "title": "Bundesinnenministerin Nancy Faeser wird Claudia Plattner zur neuen BSI-Präsidentin berufen",
                "author": "",
                "collected": "2023-01-20T15:00:14.086285",
                "hash": "e270c3a7d87051dea6c3dc14234451f884b427c32791862dacdd7a3e3d318da6",
                "review": "Claudia Plattner wird ab 1. Juli 2023 das Bundesamt für Sicherheitin der Informationstechnik (BSI) leiten.",
                "link": "https: //www.some.other.link/BSI-Praesidentin_230207.html",
                "osint_source_id": fake_source,
                "published": "2023-01-20T19:15:00+01:00",
            },
        ]

        yield Story.add_news_items(news_items_list)[0].get("ids")
