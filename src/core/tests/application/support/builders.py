from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any


def naive_utc_now_iso() -> str:
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0).isoformat()


def build_news_item_payload(
    source_id: str = "manual",
    *,
    title: str | None = None,
    title_prefix: str = "News Item",
    content: str | None = None,
    content_prefix: str = "content",
    source: str = "unit-test",
    link: str | None = None,
    story_id: str | None = None,
) -> dict[str, Any]:
    from core.model.news_item import NewsItem

    item_title = title or f"{title_prefix} {uuid.uuid4()}"
    item_content = content or f"{content_prefix}-{uuid.uuid4()}"
    item_link = link or f"https://example.invalid/{uuid.uuid4()}"
    published = naive_utc_now_iso()
    payload = {
        "id": str(uuid.uuid4()),
        "title": item_title,
        "content": item_content,
        "source": source,
        "link": item_link,
        "osint_source_id": source_id,
        "hash": NewsItem.get_hash(title=item_title, content=item_content),
        "collected": published,
        "published": published,
    }
    if story_id is not None:
        payload["story_id"] = story_id
    return payload


def build_story_payload(
    *,
    news_items: list[dict[str, Any]] | None = None,
    title: str | None = None,
    title_prefix: str = "Story",
    description: str = "story test",
    **extra_fields: Any,
) -> dict[str, Any]:
    return {
        "title": title or f"{title_prefix} {uuid.uuid4()}",
        "description": description,
        "news_items": deepcopy(news_items or []),
        **extra_fields,
    }


def create_story(
    payload: dict[str, Any] | None = None,
    *,
    news_items: list[dict[str, Any]] | None = None,
    **extra_fields: Any,
):
    from core.model.story import Story

    story_payload = deepcopy(payload) if payload is not None else build_story_payload(news_items=news_items, **extra_fields)
    result, status = Story.add(story_payload)
    assert status == 200
    story = Story.get(result["story_id"])
    assert story is not None
    return story


def build_report_payload(
    report_item_type_id: int,
    *,
    title: str | None = None,
    title_prefix: str = "Report",
    stories: list[str] | None = None,
    completed: bool = False,
    **extra_fields: Any,
) -> dict[str, Any]:
    return {
        "title": title or f"{title_prefix} {uuid.uuid4()}",
        "completed": completed,
        "report_item_type_id": report_item_type_id,
        "stories": list(stories or []),
        **extra_fields,
    }


def create_report(payload: dict[str, Any]):
    from core.model.report_item import ReportItem

    report_payload = deepcopy(payload)
    report, status = ReportItem.add(report_payload)
    assert status == 200
    persisted_report = ReportItem.get(report.id)
    assert persisted_report is not None
    return persisted_report


def create_osint_source(
    *,
    rank: int,
    source_id: str | None = None,
    name: str | None = None,
    description: str = "Story relevance test source",
    feed_url: str | None = None,
    source_type: str = "rss_collector",
):
    from core.managers.db_manager import db
    from core.model.osint_source import OSINTSource

    source = OSINTSource(
        id=source_id or f"source-{uuid.uuid4()}",
        name=name or f"Relevance Source {rank}",
        description=description,
        rank=rank,
        parameters={"FEED_URL": feed_url or f"https://example.invalid/{rank}/{uuid.uuid4()}"},
        type=source_type,
    )
    db.session.add(source)
    db.session.commit()
    return source
