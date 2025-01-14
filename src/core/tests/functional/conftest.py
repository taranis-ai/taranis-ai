import pytest


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
        source_id = source_data["id"]

        if not OSINTSource.get(source_id):
            OSINTSource.add(source_data)

        yield source_id

        OSINTSource.delete(source_id)


@pytest.fixture(scope="session")
def news_items(app, fake_source):
    yield [
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


@pytest.fixture(scope="session")
def cleanup_news_item(fake_source):
    from core.model.news_item import NewsItem

    news_item = {
        "id": "4b9a5a9e-04d7-41fc-928f-99e5ad608ebb",
        "hash": "a96e88baaff421165e90ac4bb9059971b86f88d5c2abba36d78a1264fb8e9c87",
        "title": "Test News Item 13",
        "review": "CVE-2020-1234 - Test Story 1",
        "author": "John Doe",
        "source": "https://url/13",
        "link": "https://url/13",
        "content": "CVE-2020-1234 - Test Story 1",
        "collected": "2023-08-01T17:01:04.802015",
        "published": "2023-08-01T17:01:04.801998",
        "osint_source_id": fake_source,
    }

    yield news_item

    NewsItem.delete(news_item["id"])


@pytest.fixture(scope="session")
def stories(app, news_items):
    with app.app_context():
        from core.model.story import Story
        from core.model.news_item_tag import NewsItemTag

        yield Story.add_news_items(news_items)[0].get("story_ids")

        NewsItemTag.delete_all()

        # TODO: These won't work due to a FOREIGN KEY constraint, this needs to be fixed
        #       Right now, the database is deleted after each test run, so this is not a problem
        # NewsItem.delete_all()
        # Story.delete_all()


@pytest.fixture(scope="session")
def cleanup_report_item(app):
    with app.app_context():
        from core.model.report_item import ReportItem
        from core.model.report_item_type import ReportItemType

        report_types = ReportItemType.get_all_for_collector()

        if not report_types:
            raise ValueError("No report types found")

        first_report_type = report_types[0].id

        yield {
            "id": "42",
            "title": "Test Report",
            "completed": False,
            "report_item_type_id": first_report_type,
            "stories": [],
        }

        ReportItem.delete_all()


@pytest.fixture(scope="session")
def cleanup_product(app):
    with app.app_context():
        from core.model.product import Product
        from core.model.product_type import ProductType
        from core.model.worker import PRESENTER_TYPES

        text_presenter = ProductType.get_by_type(PRESENTER_TYPES.TEXT_PRESENTER)
        if not text_presenter:
            raise ValueError("No text presenter found")

        yield {
            "id": "42",
            "title": "Test Product",
            "description": "This is a test product",
            "product_type_id": text_presenter.id,
        }

        Product.delete_all()


@pytest.fixture(scope="session")
def cleanup_story_update_data():
    yield {
        "important": True,
        "read": True,
        "title": "Updated Test Story Title",
        "description": "This is an updated test description",
        "comments": "This is an updated comment",
        "tags": ["tag1", "tag2", "tag3"],
        "summary": "This is an updated summary of the story",
        "attributes": [{"key": "priority", "value": "high"}],
        "links": [
            "https://example.com/1",
            "http://example.com/2",
        ],
    }
