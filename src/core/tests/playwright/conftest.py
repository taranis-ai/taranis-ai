import subprocess
import pytest


@pytest.fixture(scope="session")
def temporary_taranis_instance():
    # result = subprocess.run(['pwd'], capture_output=True, text=True)
    result = subprocess.run(
        ["chmod", "+x", "./tests/playwright/temporary_taranis_instance.sh"],
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["./tests/playwright/temporary_taranis_instance.sh", "up"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(
            f"Script failed with return code {result.returncode}: {result.stdout} {result.stderr}"
        )
    yield result.stdout
    result = subprocess.run(
        ["./tests/playwright/temporary_taranis_instance.sh", "down"],
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def fake_source(app, request, temporary_taranis_instance):
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
        source_id = source_data["id"]

        if not OSINTSource.get(source_id):
            OSINTSource.add(source_data)

        def teardown():
            with app.app_context():
                OSINTSource.delete(source_id)

        request.addfinalizer(teardown)

        yield source_id


@pytest.fixture(scope="session")
def news_items(app, fake_source):
    with app.app_context():
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

        yield news_items_list


@pytest.fixture(scope="session")
def stories(app, request, news_items):
    with app.app_context():
        from core.model.story import Story
        from core.model.report_item import ReportItem

        story_ids = Story.add_news_items(news_items)[0].get("ids")

        def teardown():
            with app.app_context():
                ReportItem.delete_all()
                Story.delete_all()

        request.addfinalizer(teardown)

        yield story_ids
