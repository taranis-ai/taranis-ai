import json
from copy import deepcopy
from pathlib import Path
from typing import Any


StoryPayload = dict[str, Any]

PLAYWRIGHT_STORY_FIXTURE = Path(__file__).with_name("test_stories.json")

ALLOWED_STORY_FIELDS = {
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
ALLOWED_NEWS_ITEM_FIELDS = {
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


def load_playwright_story_fixtures() -> list[StoryPayload]:
    raw_stories = json.loads(PLAYWRIGHT_STORY_FIXTURE.read_text(encoding="utf-8"))
    if not raw_stories:
        raise RuntimeError(f"No story fixtures found in {PLAYWRIGHT_STORY_FIXTURE}")
    return raw_stories


def normalize_playwright_story_payload(
    raw_story: StoryPayload,
    source_id: str,
    *,
    story_id: str | None = None,
    keep_extra_fields: bool = False,
) -> StoryPayload:
    if keep_extra_fields:
        story = deepcopy(raw_story)
    else:
        story = {key: deepcopy(value) for key, value in raw_story.items() if key in ALLOWED_STORY_FIELDS}

    if story_id is not None:
        story["id"] = story_id

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
        if keep_extra_fields:
            clean_item = deepcopy(raw_item)
        else:
            clean_item = {key: deepcopy(value) for key, value in raw_item.items() if key in ALLOWED_NEWS_ITEM_FIELDS}
        clean_item.setdefault("language", None)
        clean_item["story_id"] = story["id"]
        clean_item["osint_source_id"] = source_id
        clean_news_items.append(clean_item)
    story["news_items"] = clean_news_items

    return story
