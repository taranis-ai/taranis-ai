import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAYWRIGHT_STORY_FIXTURE = REPO_ROOT / "src/frontend/tests/playwright/test_stories.json"

DEFAULT_STORY_SOURCE_ID = "99"
LOAD_TEST_REPORT_TYPE_TITLE = "Load Testing Report Type"
LOAD_TEST_REPORT_TITLE_PREFIX = "Load Test Report"

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


def build_fake_source_payload(source_id: str = DEFAULT_STORY_SOURCE_ID) -> dict:
    return {
        "id": source_id,
        "description": "Synthetic OSINT source used by browser load tests",
        "name": "Load Test Source",
        "parameters": {"FEED_URL": "https://example.invalid/load-testing-feed.xml"},
        "type": "rss_collector",
    }


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


def load_story_seed_payloads(source_id: str = DEFAULT_STORY_SOURCE_ID, limit: int = 36) -> list[dict]:
    raw_stories = json.loads(PLAYWRIGHT_STORY_FIXTURE.read_text(encoding="utf-8"))
    stories = [_normalize_story_payload(raw_story, source_id) for raw_story in raw_stories[:limit]]

    now = datetime.now(timezone.utc).replace(microsecond=0)
    important_indices = {0, 8, 13, 17, 21}
    fresh_story_count = max(limit - 5, 1)

    for index, story in enumerate(stories):
        story["important"] = index in important_indices
        for news_item_offset, news_item in enumerate(story["news_items"]):
            if index < fresh_story_count:
                published_at = now - timedelta(hours=index + news_item_offset + 1)
            else:
                published_at = now - timedelta(days=(index - fresh_story_count + 2), hours=news_item_offset)
            published_iso = published_at.replace(tzinfo=None).isoformat()
            news_item["published"] = published_iso
            news_item["collected"] = published_iso

        if story["news_items"]:
            story["created"] = story["news_items"][0]["published"]
    return stories


def build_report_payload(story_ids: list[str], report_type_id: int, title: str, report_id: str) -> dict:
    return {
        "id": report_id,
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
