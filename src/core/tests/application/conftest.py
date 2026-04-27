import json
import uuid
from copy import deepcopy
from pathlib import Path

import pytest


_TEST_DATA_DIR = Path(__file__).resolve().parents[1] / "test_data"
_STORY_LIST_PATH = _TEST_DATA_DIR / "story_list.json"


def _load_story_list() -> list[dict]:
    return json.loads(_STORY_LIST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="class")
def fake_source(app):
    with app.app_context():
        from core.model.osint_source import OSINTSource

        source_data = {
            "id": "99",
            "description": "This is a test source",
            "name": "Test Source",
            "rank": 0,
            "parameters": {"FEED_URL": "https://url/feed.xml"},
            "type": "rss_collector",
        }
        source_id = source_data["id"]

        if not OSINTSource.get(source_id):
            OSINTSource.add(source_data)

        yield source_id

        OSINTSource.delete(source_id)


@pytest.fixture(scope="class")
def ranked_source(app):
    with app.app_context():
        from core.model.osint_source import OSINTSource

        source_data = {
            "id": "source-rank-4",
            "description": "Ranked source",
            "name": "Ranked Source",
            "rank": 4,
            "parameters": {"FEED_URL": "https://ranked.example/feed.xml"},
            "type": "rss_collector",
        }

        if existing_source := OSINTSource.get(source_data["id"]):
            OSINTSource.update(existing_source.id, {"rank": source_data["rank"]})
        else:
            OSINTSource.add(source_data)

        yield source_data["id"]

        OSINTSource.delete(source_data["id"])


@pytest.fixture(scope="class")
def rt_id_attribute():
    yield {"key": "rt_id", "value": "1/2021-01-01T01:01:01Z"}


@pytest.fixture(scope="class")
def news_items(fake_source):
    yield [
        {
            "id": "1be00eef-6ade-4818-acfc-25029531a9a5",
            "content": "TEST CONTENT ZZZZ",
            "source": "https: //www.some.link/RSSNewsfeed.xml",
            "title": "Mobile World Congress 2023",
            "author": "",
            "collected": "2022-02-21T15:00:14.086285",
            "hash": "82e6e99403686a1072d0fb2013901b843a6725ba8ac4266270f62b7614ec1adf",
            "review": "",
            "link": "https://www.some.other.link/2023.html",
            "osint_source_id": fake_source,
            "published": "2024-02-21T15:01:14.086285",
        },
        {
            "id": "0a129597-592d-45cb-9a80-3218108b29a0",
            "content": "TEST CONTENT YYYY",
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
        {
            "id": "04129597-592d-45cb-9a80-3218108b29a1",
            "content": "TEST CONTENT XXXX",
            "source": "manual",
            "title": "Anonymous News Item",
            "author": "",
            "collected": "2023-01-20T13:00:14.086285",
            "hash": "e270c3a7d87051dea6c3dc14234451f884b427c32791862dacdd7a3e3d318da1",
            "review": "Dummy review from an anonymous user.",
            "link": "https: //www.some.other.link/BSI-Praesidentin_230207.html",
            "osint_source_id": "manual",
            "last_change": "internal",
            "published": "2022-01-10T12:13:00+01:00",
        },
    ]


@pytest.fixture(scope="class")
def cleanup_news_item(fake_source):
    from core.model.news_item import NewsItem

    news_item = {
        "id": "4b9a5a9e-04d7-41fc-928f-99e5ad608ebb",
        "hash": "a96e88baaff421165e90ac4bb9059971b86f88d5c2abba36d78a1264fb8e9c87",
        "title": "<b>Test News Item 13</b>",
        "review": "CVE-2020-1234 - Test Story 1",
        "author": "John Doe",
        "source": "manual submission",
        "link": "https://url/13 path?q=a b",
        "content": "<p>CVE-2020-1234 - Test Story 1</p>",
        "collected": "2023-08-01T17:01:04.802015+02:00",
        "published": "2023-08-01T17:01:04.801998+02:00",
        "updated": "2024-01-02T03:04:05+02:00",
        "osint_source_id": fake_source,
    }

    yield news_item

    NewsItem.delete(news_item["id"])


@pytest.fixture
def cleanup_ranked_news_item(ranked_source):
    from core.model.news_item import NewsItem

    news_item = {
        "id": "4b9a5a9e-04d7-41fc-928f-99e5ad608ebc",
        "hash": "a96e88baaff421165e90ac4bb9059971b86f88d5c2abba36d78a1264fb8e9c88",
        "title": "Ranked News Item",
        "review": "Ranked source story",
        "author": "Jane Doe",
        "source": "https://url/ranked",
        "link": "https://url/ranked",
        "content": "Ranked source story",
        "collected": "2023-08-02T17:01:04.802015",
        "published": "2023-08-02T17:01:04.801998",
        "osint_source_id": ranked_source,
    }

    yield news_item

    NewsItem.delete(news_item["id"])


@pytest.fixture
def cleanup_manual_news_item():
    from core.model.news_item import NewsItem

    news_item = {
        "id": "4b9a5a9e-04d7-41fc-928f-99e5ad608ebd",
        "hash": "a96e88baaff421165e90ac4bb9059971b86f88d5c2abba36d78a1264fb8e9c89",
        "title": "Manual News Item",
        "review": "Manual source story",
        "author": "Analyst",
        "source": "manual",
        "link": "https://url/manual",
        "content": "Manual source story",
        "collected": "2023-08-03T17:01:04.802015",
        "published": "2023-08-03T17:01:04.801998",
        "osint_source_id": "manual",
    }

    yield news_item

    NewsItem.delete(news_item["id"])


@pytest.fixture(scope="class")
def cleanup_news_item_2(fake_source):
    from core.model.news_item import NewsItem

    news_item = {
        "id": "4b9a5a9e-04d7-41fc-928f-99e5ad608ebt",
        "hash": "a96e88baaff421165e90ac4bb9059971b86f88d5c2abba36d78a1264fb8e9c46",
        "title": "Test News Item 14",
        "review": "CVE-2020-5678 - Test Story 1 - news item 2",
        "author": "John Doe",
        "source": "https://url/13",
        "link": "https://url/13",
        "content": "CVE-2020-5678 - Test Story 1",
        "collected": "2023-08-01T17:01:04.802015",
        "published": "2023-08-01T17:01:04.801998",
        "osint_source_id": fake_source,
    }

    yield news_item

    NewsItem.delete(news_item["id"])


@pytest.fixture(scope="class")
def stories(app, news_items):
    with app.app_context():
        from core.model.news_item import NewsItem
        from core.model.story import Story, StoryNewsItemAttribute

        result = Story.add_news_items(news_items)

        yield result[0].get("story_ids")

        StoryNewsItemAttribute.delete_all()
        NewsItem.delete_all()
        Story.delete_all()


@pytest.fixture(scope="class")
def story_filter_data(app, stories, fake_source, cleanup_report_item):
    with app.app_context():
        from core.managers.db_manager import db
        from core.model.news_item import NewsItem
        from core.model.osint_source import OSINTSource, OSINTSourceGroup
        from core.model.report_item import ReportItem
        from core.model.story import Story, StoryNewsItemAttribute

        extra_source = OSINTSource(
            id="story-filter-source-extra",
            name="Story Filter Extra Source",
            description="Additional source for story filter tests",
            type="rss_collector",
            parameters={"FEED_URL": "https://example.invalid/story-filter-extra.xml"},
        )
        source_group = OSINTSourceGroup(
            id="story-filter-group",
            name="Story Filter Group",
            description="Source group for story filter tests",
        )

        db.session.add_all([extra_source, source_group])
        source_group.osint_sources.append(OSINTSource.get(fake_source))
        db.session.commit()

        extra_story_payload = {
            "title": "Story Filter Extra Source Story",
            "news_items": [
                {
                    "id": "story-filter-news-item-extra",
                    "title": "Story Filter Extra Source Story",
                    "content": "Story Filter Extra Source Story Content",
                    "source": "unit-test",
                    "link": "https://example.invalid/story-filter-extra",
                    "osint_source_id": extra_source.id,
                    "hash": NewsItem.get_hash(
                        title="Story Filter Extra Source Story",
                        content="Story Filter Extra Source Story Content",
                    ),
                    "collected": "2025-01-01T00:00:00",
                    "published": "2025-01-01T00:00:00",
                }
            ],
        }
        result, status = Story.add(extra_story_payload)
        assert status == 200

        grouped_flagged = Story.get(stories[0])
        grouped_plain = Story.get(stories[1])
        manual_important = Story.get(stories[2])
        source_only = Story.get(result["story_id"])
        assert grouped_flagged is not None
        assert grouped_plain is not None
        assert manual_important is not None
        assert source_only is not None

        grouped_flagged.read = True
        grouped_flagged.important = True
        grouped_flagged.relevance = 10

        grouped_plain.read = False
        grouped_plain.important = False
        grouped_plain.relevance = 0

        manual_important.read = False
        manual_important.important = True
        manual_important.relevance = 0

        source_only.read = True
        source_only.important = False
        source_only.relevance = 5
        db.session.commit()

        assert grouped_flagged.set_tags(["filter-alpha"])[1] == 200
        assert grouped_plain.set_tags(["filter-beta"])[1] == 200
        assert manual_important.set_tags(["filter-gamma"])[1] == 200
        assert source_only.set_tags(["filter-delta"])[1] == 200

        report_payload = deepcopy(cleanup_report_item)
        report_payload["id"] = "story-filter-report-item"
        report_payload["title"] = "Story Filter Report Item"
        report_payload["stories"] = [grouped_flagged.id]
        report_item, status = ReportItem.add(report_payload)
        assert status == 200
        assert isinstance(report_item, ReportItem)

        yield {
            "stories": {
                "grouped_flagged": grouped_flagged.id,
                "grouped_plain": grouped_plain.id,
                "manual_important": manual_important.id,
                "source_only": source_only.id,
            },
            "sources": {
                "grouped": fake_source,
                "source_only": extra_source.id,
            },
            "groups": {
                "primary": source_group.id,
            },
            "tags": {
                "alpha": "filter-alpha",
                "beta": "filter-beta",
                "gamma": "filter-gamma",
                "delta": "filter-delta",
            },
        }

        ReportItem.delete_all()
        StoryNewsItemAttribute.delete_all()
        NewsItem.delete_all()
        Story.delete_all()
        OSINTSourceGroup.delete(source_group.id)
        OSINTSource.delete(extra_source.id)


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
        from models.types import PRESENTER_TYPES

        from core.model.product import Product
        from core.model.product_type import ProductType

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


@pytest.fixture
def workflow_publish_resources(app):
    with app.app_context():
        from models.types import PRESENTER_TYPES, PUBLISHER_TYPES

        from core.managers.db_manager import db
        from core.model.attribute import Attribute, AttributeType
        from core.model.product import Product
        from core.model.product_type import ProductType
        from core.model.publisher_preset import PublisherPreset
        from core.model.report_item import ReportItem
        from core.model.report_item_type import ReportItemType

        suffix = uuid.uuid4().hex

        summary_attribute = Attribute(
            name=f"workflow_summary_{suffix}",
            description="Workflow summary attribute",
            attribute_type=AttributeType.STRING,
            default_value="Default executive summary",
        )
        recommendation_attribute = Attribute(
            name=f"workflow_recommendation_{suffix}",
            description="Workflow recommendation attribute",
            attribute_type=AttributeType.STRING,
            default_value="Default recommendation",
        )
        db.session.add_all([summary_attribute, recommendation_attribute])
        db.session.flush()

        report_type = ReportItemType(
            title=f"Workflow Report Type {suffix}",
            description="Workflow report type for publish endpoint tests",
            attribute_groups=[
                {
                    "index": 0,
                    "title": "Workflow Group",
                    "description": "Workflow attributes",
                    "attribute_group_items": [
                        {
                            "index": 0,
                            "attribute_id": summary_attribute.id,
                            "title": "Executive Summary",
                            "description": "Summary field",
                            "required": False,
                        },
                        {
                            "index": 1,
                            "attribute_id": recommendation_attribute.id,
                            "title": "Recommendation",
                            "description": "Recommendation field",
                            "required": False,
                        },
                    ],
                }
            ],
        )
        db.session.add(report_type)
        db.session.flush()

        product_type = ProductType(
            title=f"Workflow Product Type {suffix}",
            type=PRESENTER_TYPES.HTML_PRESENTER,
            description="Workflow product type",
            parameters={"TEMPLATE_PATH": "cert_at_daily_report.html"},
            report_types=[report_type.id],
        )
        publisher_preset = PublisherPreset(
            id=f"workflow-publisher-{suffix}",
            name=f"Workflow Publisher {suffix}",
            description="Workflow publisher preset",
            type=PUBLISHER_TYPES.FTP_PUBLISHER,
            parameters={"FTP_URL": "ftp://example.invalid/out"},
        )

        db.session.add_all([product_type, publisher_preset])
        db.session.commit()

        yield {
            "report_type_id": report_type.id,
            "product_type_id": product_type.id,
            "publisher_preset_id": publisher_preset.id,
            "group_title": "Workflow Group",
            "summary_title": "Executive Summary",
            "summary_default": "Default executive summary",
            "recommendation_title": "Recommendation",
            "recommendation_default": "Default recommendation",
        }

        Product.delete_all()
        ReportItem.delete_all()

        if PublisherPreset.get(publisher_preset.id):
            db.session.delete(PublisherPreset.get(publisher_preset.id))
        if ProductType.get(product_type.id):
            db.session.delete(ProductType.get(product_type.id))
        if ReportItemType.get(report_type.id):
            db.session.delete(ReportItemType.get(report_type.id))
        if Attribute.get(summary_attribute.id):
            db.session.delete(Attribute.get(summary_attribute.id))
        if Attribute.get(recommendation_attribute.id):
            db.session.delete(Attribute.get(recommendation_attribute.id))
        db.session.commit()


@pytest.fixture(scope="class")
def pdf_product(app):
    with app.app_context():
        from models.types import PRESENTER_TYPES

        from core.model.product import Product
        from core.model.product_type import ProductType

        pdf_presenter = ProductType.get_by_type(PRESENTER_TYPES.PDF_PRESENTER)
        if not pdf_presenter:
            raise ValueError("No pdf presenter found")

        product_data = {
            "id": str(uuid.uuid4()),
            "title": "Test Product",
            "description": "This is a test product",
            "product_type_id": pdf_presenter.id,
        }

        yield Product.add(product_data)
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
    }


@pytest.fixture(scope="class")
def report_items(app):
    with app.app_context():
        from core.model.report_item import ReportItem, ReportItemAttribute
        from core.model.report_item_type import ReportItemType
        from core.model.role import TLPLevel

        if osint_report_type := ReportItemType.get_by_title("OSINT Report"):
            osint_report_type_id = osint_report_type.id
        else:
            raise ValueError("OSINT Report type not found")

        if vulnerability_report_type := ReportItemType.get_by_title("Vulnerability Report"):
            vulnerability_report_type_id = vulnerability_report_type.id
        else:
            raise ValueError("Vulnerability Report type not found")

        if cert_report_type := ReportItemType.get_by_title("CERT Report"):
            cert_report_type_id = cert_report_type.id
        else:
            raise ValueError("CERT Report type not found")

        report_item1_data = {
            "id": "c285fe34-474d-4197-8b1a-564ee46e13f5",
            "title": "OSINT report Item with TLP:Clear",
            "completed": False,
            "report_item_type_id": osint_report_type_id,
        }

        report_item2_data = {
            "id": "3f98a483-ede6-4614-b329-76f85163d810",
            "title": "OSINT report Item with TLP:Amber",
            "completed": False,
            "report_item_type_id": osint_report_type_id,
        }

        report_item3_data = {
            "id": "4f61e069-bbd0-4fdc-b719-db2a801cb7de",
            "title": "CERT Report Item with TLP:Red",
            "completed": False,
            "report_item_type_id": vulnerability_report_type_id,
        }

        report_item4_data = {
            "id": "a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6",
            "title": "CERT Report without TLP",
            "completed": False,
            "report_item_type_id": cert_report_type_id,
        }

        report_item_clear, _ = ReportItem.add(report_item1_data, None)
        report_item_amber, _ = ReportItem.add(report_item2_data, None)
        report_item_red, _ = ReportItem.add(report_item3_data, None)
        report_item_without_TLP, _ = ReportItem.add(report_item4_data, None)

        if tlp_attribute := ReportItemAttribute.find_attribute_by_title(report_item_amber.id, "TLP"):
            report_item_amber.update_attributes({str(tlp_attribute.id): TLPLevel.AMBER.value}, True)

        if tlp_attribute := ReportItemAttribute.find_attribute_by_title(report_item_red.id, "TLP"):
            report_item_red.update_attributes({str(tlp_attribute.id): TLPLevel.RED.value}, True)

        yield report_item_clear, report_item_amber, report_item_red, report_item_without_TLP

        ReportItem.delete_all()


@pytest.fixture(scope="function")
def stories_with_tlp(app, fake_source):
    with app.app_context():
        from core.model.news_item import NewsItem
        from core.model.news_item_attribute import NewsItemAttribute
        from core.model.role import TLPLevel
        from core.model.story import Story, StoryNewsItemAttribute

        news_items = [
            {
                "id": "tlp-news-green",
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
                "id": "tlp-news-clear",
                "title": "Plain News Item",
                "content": "This is just a regular news item.",
                "source": "https://example.com/news/plain",
                "osint_source_id": fake_source,
                "collected": "2024-01-01T01:00:00",
                "published": "2024-01-01T01:00:00",
                "review": "Another review",
                "hash": "plain-news-hash",
            },
            {
                "id": "tlp-news-red",
                "title": "Another TLP News Item",
                "content": "This is another TLP-related content.",
                "source": "https://example.com/news/tlp2",
                "osint_source_id": fake_source,
                "collected": "2024-01-01T02:00:00",
                "published": "2024-01-01T02:00:00",
                "review": "Yet another review",
                "hash": "tlp-news-hash-2",
                "attributes": [{"key": "TLP", "value": TLPLevel.RED.value}],
            },
        ]

        result, _ = Story.add_news_items(news_items)
        yield result

        StoryNewsItemAttribute.delete_all()
        NewsItemAttribute.delete_all()
        NewsItem.delete_all()
        Story.delete_all()


@pytest.fixture(scope="class")
def full_story(fake_source):
    story = _load_story_list()
    story[0].get("news_items")[0]["osint_source_id"] = fake_source
    yield story


@pytest.fixture(scope="class")
def story_payload_factory(fake_source):
    from core.model.news_item import NewsItem

    story_templates = _load_story_list()

    def _build(index: int = 1) -> dict:
        suffix = uuid.uuid4().hex
        story = deepcopy(story_templates[index])
        story["id"] = str(uuid.uuid4())
        story["title"] = f"{story['title']} {suffix}"

        for item_number, news_item in enumerate(story.get("news_items", []), start=1):
            news_item["id"] = str(uuid.uuid4())
            news_item["story_id"] = story["id"]
            news_item["osint_source_id"] = fake_source
            news_item["title"] = f"{news_item['title']} {suffix}-{item_number}"
            news_item["link"] = f"https://example.invalid/story/{suffix}/{item_number}"
            news_item["hash"] = NewsItem.get_hash(
                title=news_item["title"],
                link=news_item["link"],
                content=news_item["content"],
            )

        return story

    return _build


@pytest.fixture(scope="class")
def full_story_with_multiple_items_id(fake_source):
    from core.model.story import NewsItem, Story, StoryNewsItemAttribute

    story = _load_story_list()[1]
    story["news_items"][0]["osint_source_id"] = fake_source
    story["news_items"][1]["osint_source_id"] = fake_source

    result = Story.add(story)
    yield result[0].get("story_id"), story

    StoryNewsItemAttribute.delete_all()
    NewsItem.delete_all()
    Story.delete_all()


@pytest.fixture
def story_search_story_payload(story_payload_factory):
    yield story_payload_factory(index=1)


@pytest.fixture
def story_search_story_payloads(story_payload_factory):
    yield story_payload_factory(index=1), story_payload_factory(index=1)


@pytest.fixture
def seed_story_payload_factory():
    from tests.application.support.builders import build_news_item_payload, build_story_payload

    def _build() -> dict:
        return build_story_payload(
            title_prefix="Seed Story",
            description="seed story",
            news_items=[
                build_news_item_payload(
                    source_id="manual",
                    title_prefix="Seed News Item",
                    content_prefix="content",
                    source="seed-test",
                    link="https://example.invalid/seed-test",
                )
            ],
        )

    return _build


@pytest.fixture
def seed_report_payload_factory(sample_report_type):
    from tests.application.support.builders import build_report_payload

    def _build(**extra_fields) -> dict:
        return build_report_payload(sample_report_type.id, title_prefix="Seed Report", **extra_fields)

    return _build


@pytest.fixture
def story_relevance_news_item_payload_factory():
    from tests.application.support.builders import build_news_item_payload

    def _build(source_id: str, title: str | None = None) -> dict:
        return build_news_item_payload(
            source_id=source_id,
            title=title,
            title_prefix="Story Relevance News Item",
            source="story-relevance-test",
        )

    return _build


@pytest.fixture
def story_relevance_story_payload_factory():
    from tests.application.support.builders import build_story_payload

    def _build(news_items: list[dict], **extra_fields) -> dict:
        return build_story_payload(
            news_items=news_items,
            title_prefix="Story Relevance Story",
            description="story relevance test",
            **extra_fields,
        )

    return _build


@pytest.fixture
def story_relevance_report_payload_factory(sample_report_type):
    from tests.application.support.builders import build_report_payload

    def _build(**extra_fields) -> dict:
        return build_report_payload(sample_report_type.id, title_prefix="Story Relevance Report", **extra_fields)

    return _build


@pytest.fixture(scope="class")
def misp_story_from_news_items_id(app, news_items):
    from core.model.story import NewsItem, Story, StoryNewsItemAttribute

    story_data = [
        {
            "id": "c285fe34-474d-4197-8b1a-564ee46e13f5",
            "title": "Test title",
            "attributes": [{"key": "hey", "value": "hou"}],
            "news_items": news_items,
        }
    ]
    story_ids = []
    with app.app_context():
        result, _ = Story.add_or_update_for_misp(story_data)
        story_ids = result.get("details", {}).get("story_ids", [])
        assert story_ids, f"Should be story ids, got {result.get('details', {}).get('errors')}"
        assert len(story_ids) == 1

        yield story_ids[0], story_data[0]

        StoryNewsItemAttribute.delete_all()
        NewsItem.delete_all()
        Story.delete_all()


@pytest.fixture(scope="class")
def story_conflict_resolution_1(news_items, cleanup_news_item):
    yield {
        "resolution": {
            "title": "Updated Test Story Title",
            "description": "This is an updated test description",
            "comments": "This is an updated comment",
            "summary": "This is an updated summary of the story",
            "attributes": [{"key": "priority", "value": "high"}],
            "links": ["https://example.com/1", "http://example.com/2"],
            "news_items": news_items[:2] + [cleanup_news_item],
        }
    }


@pytest.fixture(scope="class")
def cleanup_publisher(app):
    with app.app_context():
        from core.model.publisher_preset import PublisherPreset

        publisher_data = {
            "id": "99",
            "name": "Test Publisher",
            "description": "This is a test email publisher",
            "type": "email_publisher",
            "parameters": {
                "SMTP_SERVER_ADDRESS": "smtp.example.com",
                "SMTP_SERVER_PORT": "587",
                "SERVER_TLS": "true",
                "EMAIL_USERNAME": "publisher@example.com",
                "EMAIL_PASSWORD": "password",
                "EMAIL_SENDER": "publisher@example.com",
                "EMAIL_RECIPIENT": "recipient@example.com",
                "EMAIL_SUBJECT": "Functional Test Publication",
            },
        }

        yield publisher_data

        if PublisherPreset.get(publisher_data["id"]):
            PublisherPreset.delete(publisher_data["id"])


def remap_result_keys(payload: dict, stories) -> dict:
    payload = deepcopy(payload)

    old = payload["result"]
    story_ids = [str(getattr(s, "id", s)) for s in stories]

    payload["result"] = {story_id: tags_dict for story_id, tags_dict in zip(story_ids, old.values())}
    return payload


@pytest.fixture
def wordlist_bot_result(stories):
    from tests.test_data.bot_test_data import wordlist_bot_result as base

    yield remap_result_keys(base, stories)


@pytest.fixture
def ioc_bot_result(stories):
    from tests.test_data.bot_test_data import ioc_bot_result as base

    yield remap_result_keys(base, stories)


@pytest.fixture
def nlp_bot_result(stories):
    from tests.test_data.bot_test_data import nlp_bot as base

    yield remap_result_keys(base, stories)


@pytest.fixture
def applied_wordlist(client, api_header, wordlist_bot_result):
    resp = client.post("/api/tasks", json=wordlist_bot_result, headers=api_header)
    assert resp.status_code == 200
    assert resp.get_json().get("status") == "SUCCESS"
    return resp


@pytest.fixture
def applied_ioc(client, api_header, ioc_bot_result):
    resp = client.post("/api/tasks", json=ioc_bot_result, headers=api_header)
    assert resp.status_code == 200
    assert resp.get_json().get("status") == "SUCCESS"
    return resp


@pytest.fixture
def applied_nlp(client, api_header, nlp_bot_result):
    resp = client.post("/api/tasks", json=nlp_bot_result, headers=api_header)
    assert resp.status_code == 200
    assert resp.get_json().get("status") == "SUCCESS"
    return resp
