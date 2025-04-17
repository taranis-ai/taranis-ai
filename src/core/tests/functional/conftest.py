import pytest


@pytest.fixture(scope="class")
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


@pytest.fixture(scope="class")
def rt_id_attribute():
    yield {"key": "rt_id", "value": "1/2021-01-01T01:01:01Z"}


@pytest.fixture(scope="class")
def news_items(fake_source):
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


@pytest.fixture(scope="class")
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


@pytest.fixture(scope="class")
def stories(app, news_items):
    with app.app_context():
        from core.model.story import Story, StoryNewsItemAttribute
        from core.model.news_item import NewsItem

        result = Story.add_news_items(news_items)

        yield result[0].get("story_ids")

        StoryNewsItemAttribute.delete_all()
        NewsItem.delete_all()
        Story.delete_all()


@pytest.fixture(scope="class")
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


@pytest.fixture(scope="class")
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


@pytest.fixture(scope="class")
def cleanup_story_update_data(rt_id_attribute):
    yield {
        "important": True,
        "read": True,
        "title": "Updated Test Story Title",
        "description": "This is an updated test description",
        "comments": "This is an updated comment",
        "summary": "This is an updated summary of the story",
        "attributes": [
            {"key": "priority", "value": "high"},
            rt_id_attribute,
        ],
        "links": [
            "https://example.com/1",
            "http://example.com/2",
        ],
    }


@pytest.fixture(scope="class")
def test_user(app):
    with app.app_context():
        from core.model.user import User

        user_data = {"id": 222, "name": "Test User", "username": "Test User", "organization": "Test Org", "roles": ["role1", "role2"]}
        yield User.add(user_data)

        User.delete(user_data["id"])


@pytest.fixture(scope="class")
def report_items(app, test_user):
    with app.app_context():
        from core.model.report_item import ReportItem, ReportItemAttribute
        from core.model.report_item_type import ReportItemType
        from core.model.report_item import AttributeType
        from core.model.role import TLPLevel

        report_types = ReportItemType.get_all_for_collector()
        if not report_types:
            raise ValueError("No report types found")
        report_title_ids = {rt.title: rt.id for rt in report_types}
        osint_repot_id = report_title_ids.get("OSINT Report")
        cert_repot_id = report_title_ids.get("CERT Report")

        report_item1_data = {
            "id": "c285fe34-474d-4197-8b1a-564ee46e13f5",
            "title": "OSINT report Item with TLP:Clear",
            "completed": False,
            "report_item_type_id": osint_repot_id,
        }

        report_item2_data = {
            "id": "3f98a483-ede6-4614-b329-76f85163d810",
            "title": "OSINT report Item with TLP:Red",
            "completed": False,
            "report_item_type_id": osint_repot_id,
        }

        report_item3_data = {
            "id": "4f61e069-bbd0-4fdc-b719-db2a801cb7de",
            "title": "CERT Report Item without TLP level",
            "completed": False,
            "report_item_type_id": cert_repot_id,
        }

        report_item1, _ = ReportItem.add(report_item1_data, test_user)
        report_item2, _ = ReportItem.add(report_item2_data, test_user)
        report_item3, _ = ReportItem.add(report_item3_data, test_user)

        clear_tlp_attr = ReportItemAttribute(attribute_type=AttributeType.TLP, group_title="Summary", value=TLPLevel.CLEAR.value)
        red_tlp_attr = ReportItemAttribute(attribute_type=AttributeType.TLP, group_title="Summary", value=TLPLevel.AMBER.value)

        report_item1.attributes.append(clear_tlp_attr)
        report_item2.attributes.append(red_tlp_attr)

        yield report_item1, report_item2, report_item3

        ReportItem.delete_all()


@pytest.fixture(scope="function")
def stories_with_tlp(app, fake_source):
    with app.app_context():
        from core.model.story import Story, StoryNewsItemAttribute
        from core.model.news_item import NewsItem
        from core.model.news_item_attribute import NewsItemAttribute
        from core.model.role import TLPLevel

        news_items = [
            {
                "id": "tlp-news-001",
                "title": "TLP News Item",
                "content": "This is TLP-related content.",
                "source": "https://example.com/news/tlp",
                "osint_source_id": fake_source,
                "collected": "2024-01-01T00:00:00",
                "published": "2024-01-01T00:00:00",
                "review": "Some review",
                "hash": "tlp-news-hash",
                "attributes": [{"key": "TLP", "value": TLPLevel.GREEN.value}],
            },
            {
                "id": "plain-news-002",
                "title": "Plain News Item",
                "content": "This is just a regular news item.",
                "source": "https://example.com/news/plain",
                "osint_source_id": fake_source,
                "collected": "2024-01-01T01:00:00",
                "published": "2024-01-01T01:00:00",
                "review": "Another review",
                "hash": "plain-news-hash",
            },
        ]

        result, _ = Story.add_news_items(news_items)
        yield result.get("story_ids")

        StoryNewsItemAttribute.delete_all()
        NewsItem.delete_all()
        NewsItemAttribute.delete_all()
        Story.delete_all()
