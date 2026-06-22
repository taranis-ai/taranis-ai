import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

from uuid_extensions import uuid7str

FRONTEND_TESTS_ROOT = Path(__file__).resolve().parents[2]
PLAYWRIGHT_STORY_FIXTURE = FRONTEND_TESTS_ROOT / "playwright/test_stories.json"

DEFAULT_STORY_SOURCE_ID = "99"
LOAD_TEST_REPORT_TYPE_TITLE = "Load Testing Report Type"
LOAD_TEST_REPORT_TITLE_PREFIX = "Load Test Report"
DEFAULT_SOURCE_COUNT = 10
DEFAULT_STORY_COUNT = 1000
DEFAULT_REPORT_TYPE_COUNT = 5
DEFAULT_REPORT_COUNT = 250

LOAD_TEST_REPORT_TYPE_DEFINITION: dict = {
    "title": LOAD_TEST_REPORT_TYPE_TITLE,
    "description": "Report type used by the manual browser load test harness.",
    "attribute_groups": [
        {
            "title": "Metadata",
            "description": "Summary metadata for browser load testing.",
            "index": 0,
            "attribute_group_items": [
                {
                    "title": "Report Classification",
                    "description": "Traffic light protocol classification.",
                    "index": 0,
                    "attribute": "TLP",
                },
                {
                    "title": "Summary",
                    "description": "High-level summary.",
                    "index": 1,
                    "attribute": "Text Area",
                },
                {
                    "title": "Related Story",
                    "description": "Linked story.",
                    "index": 2,
                    "attribute": "Story",
                },
            ],
        }
    ],
}


def build_fake_source_payload(source_id: str = DEFAULT_STORY_SOURCE_ID, *, index: int = 1) -> dict:
    source_name = "Load Test Source" if index == 1 else f"Load Test Source {index}"
    return {
        "id": source_id,
        "description": "Synthetic OSINT source used by browser load tests",
        "name": source_name,
        "parameters": {"FEED_URL": "https://example.invalid/load-testing-feed.xml"},
        "type": "rss_collector",
    }


def build_source_ids(source_id: str = DEFAULT_STORY_SOURCE_ID, count: int = DEFAULT_SOURCE_COUNT) -> list[str]:
    if count < 1:
        raise ValueError("source count must be at least 1")
    if count == 1:
        return [source_id]
    if source_id.isdigit():
        start = int(source_id)
        return [str(start + offset) for offset in range(count)]
    return [source_id] + [f"{source_id}-{index}" for index in range(2, count + 1)]


def build_report_type_titles(
    base_title: str = LOAD_TEST_REPORT_TYPE_TITLE,
    count: int = DEFAULT_REPORT_TYPE_COUNT,
) -> list[str]:
    if count < 1:
        raise ValueError("report type count must be at least 1")
    return [base_title] + [f"{base_title} {index}" for index in range(2, count + 1)]


def _normalize_story_payload(raw_story: dict, source_id: str) -> dict:
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
    allowed_news_item_fields = {
        "id",
        "title",
        "content",
        "author",
        "source",
        "link",
        "language",
        "review",
        "collected",
        "published",
        "story_id",
        "hash",
    }

    story = {key: deepcopy(value) for key, value in raw_story.items() if key in allowed_story_fields}
    story.setdefault("description", "")
    story.setdefault("comments", "")
    story.setdefault("summary", "")
    story.setdefault("read", False)
    story.setdefault("important", False)
    story.setdefault("likes", 0)
    story.setdefault("dislikes", 0)
    story.setdefault("relevance", 0)

    clean_news_items = []
    for raw_item in raw_story.get("news_items", []):
        clean_item = {key: deepcopy(value) for key, value in raw_item.items() if key in allowed_news_item_fields}
        clean_item.setdefault("language", None)
        clean_item["story_id"] = story["id"]
        clean_item["osint_source_id"] = source_id
        clean_news_items.append(clean_item)
    story["news_items"] = clean_news_items
    return story


def _build_story_identifier() -> str:
    return uuid7str()


def _build_news_item_identifier() -> str:
    return uuid7str()


def _build_news_item_hash(story_index: int, news_item_index: int) -> str:
    return f"load-hash-{story_index}-{news_item_index}"


def load_story_seed_payloads(
    source_ids: list[str] | None = None,
    limit: int = DEFAULT_STORY_COUNT,
) -> list[dict]:
    if limit < 1:
        raise ValueError("story count must be at least 1")

    raw_stories = json.loads(PLAYWRIGHT_STORY_FIXTURE.read_text(encoding="utf-8"))
    if not raw_stories:
        raise RuntimeError(f"No load-test story fixtures found in {PLAYWRIGHT_STORY_FIXTURE}")

    if source_ids is None:
        source_ids = build_source_ids(DEFAULT_STORY_SOURCE_ID, 1)
    if not source_ids:
        raise ValueError("source_ids must not be empty")

    now = datetime.now(timezone.utc).replace(microsecond=0)
    fresh_story_count = max(limit - 5, 1)
    stories: list[dict] = []

    for index in range(limit):
        template = raw_stories[index % len(raw_stories)]
        source_id = source_ids[index % len(source_ids)]
        story = _normalize_story_payload(template, source_id)
        story["id"] = _build_story_identifier()
        story["important"] = index % 10 == 0

        if index >= len(raw_stories):
            story["title"] = f"{story['title']} #{index + 1}"

        for news_item_offset, news_item in enumerate(story["news_items"]):
            news_item["id"] = _build_news_item_identifier()
            news_item["hash"] = _build_news_item_hash(index + 1, news_item_offset + 1)
            news_item["story_id"] = story["id"]
            news_item["osint_source_id"] = source_id
            if index < fresh_story_count:
                published_at = now - timedelta(hours=index + news_item_offset + 1)
            else:
                published_at = now - timedelta(
                    days=(index - fresh_story_count + 2),
                    hours=news_item_offset,
                )
            published_iso = published_at.replace(tzinfo=None).isoformat()
            news_item["published"] = published_iso
            news_item["collected"] = published_iso
            news_item["link"] = f"https://example.invalid/load-testing/story/{index + 1}/item/{news_item_offset + 1}"

        if story["news_items"]:
            story["created"] = story["news_items"][0]["published"]
        stories.append(story)
    return stories


def build_report_payload(
    story_ids: list[str],
    report_type_id: str,
    title: str,
    report_id: str | None = None,
) -> dict:
    return {
        "id": report_id or uuid7str(),
        "title": title,
        "report_item_type_id": report_type_id,
        "completed": False,
        "stories": story_ids,
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
                "description": "High-level overview of the loaded stories",
                "value": f"{title} seeded for browser load testing.",
                "index": 1,
                "required": False,
                "attribute_type": "TEXT",
                "group_title": "Metadata",
                "render_data": {},
            },
            {
                "title": "Related Story",
                "description": "One representative story",
                "value": ",".join(story_ids[:1]),
                "index": 2,
                "required": False,
                "attribute_type": "STORY",
                "group_title": "Metadata",
                "render_data": {},
            },
        ],
    }
