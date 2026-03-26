from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from core.model.news_item import NewsItem
from core.model.osint_source import OSINTSource
from core.model.report_item import ReportItem
from core.model.story import Story
from core.model.user import User


def _now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def _create_source(rank: int) -> OSINTSource:
    source = OSINTSource(
        id=f"relevance-source-{uuid.uuid4()}",
        name=f"Relevance Source {rank}",
        description="Story relevance test source",
        rank=rank,
        parameters={"FEED_URL": f"https://example.invalid/{rank}/{uuid.uuid4()}"},
        type="rss_collector",
    )
    from core.managers.db_manager import db

    db.session.add(source)
    db.session.commit()
    return source


def _news_item_payload(source_id: str, title: str | None = None) -> dict[str, str]:
    title = title or f"Story Relevance News Item {uuid.uuid4()}"
    published = _now()
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "content": f"{title} content",
        "source": "story-relevance-test",
        "link": f"https://example.invalid/{uuid.uuid4()}",
        "osint_source_id": source_id,
        "hash": NewsItem.get_hash(title=title, content=f"{title} content"),
        "collected": published,
        "published": published,
    }


def _create_story(news_items: list[dict[str, str]], **extra_fields) -> Story:
    payload = {
        "title": extra_fields.pop("title", f"Story Relevance Story {uuid.uuid4()}"),
        "description": extra_fields.pop("description", "story relevance test"),
        "news_items": news_items,
        **extra_fields,
    }
    result, status = Story.add(payload)
    assert status == 200
    return Story.get(result["story_id"])


def _create_report(sample_report_type, title: str | None = None) -> ReportItem:
    payload = {
        "title": title or f"Story Relevance Report {uuid.uuid4()}",
        "completed": False,
        "report_item_type_id": sample_report_type.id,
        "stories": [],
    }
    report, status = ReportItem.add(payload)
    assert status == 200
    return ReportItem.get(report.id)


@pytest.mark.usefixtures("app")
def test_ranked_story_uses_ad_hoc_source_relevance_and_hides_breakdown(session):
    source = _create_source(rank=4)
    story = _create_story([_news_item_payload(source.id)])

    detail = story.to_detail_dict()

    assert story.relevance == 4
    assert story.relevance_source == 4
    assert story.relevance_override == 0
    assert "relevance_breakdown" not in detail


@pytest.mark.usefixtures("app")
def test_explicit_relevance_payload_becomes_override(session):
    story = _create_story([_news_item_payload("manual")], relevance=5)

    assert story.relevance == 5
    assert story.relevance_source == 0
    assert story.relevance_override == 5


@pytest.mark.usefixtures("app")
def test_marking_story_important_adds_relevance_bonus(session):
    story = _create_story([_news_item_payload("manual")])

    response, status = Story.update(story.id, {"important": True})
    assert status == 200

    updated_story = Story.get(story.id)
    assert updated_story is not None
    assert updated_story.relevance == 3
    assert updated_story.relevance_feedback == 3


@pytest.mark.usefixtures("app")
def test_report_assignment_adds_bonus_once(session, sample_report_type):
    admin = User.find_by_name("admin")
    assert admin is not None

    story = _create_story([_news_item_payload("manual")])
    report_one = _create_report(sample_report_type, title="Relevance Report One")
    report_two = _create_report(sample_report_type, title="Relevance Report Two")

    response, status = ReportItem.add_stories(report_one.id, [story.id], admin)
    assert status == 200, response

    story = Story.get(story.id)
    assert story is not None
    assert story.relevance == 3
    assert story.relevance_feedback == 3

    response, status = ReportItem.add_stories(report_two.id, [story.id], admin)
    assert status == 200, response

    story = Story.get(story.id)
    assert story is not None
    assert story.relevance == 3
    assert story.relevance_feedback == 3


@pytest.mark.usefixtures("app")
def test_grouping_uses_max_source_rank_instead_of_size_bonus(session):
    low_source = _create_source(rank=1)
    high_source = _create_source(rank=5)

    first_story = _create_story([_news_item_payload(low_source.id)], title="Low rank story")
    second_story = _create_story([_news_item_payload(high_source.id)], title="High rank story")

    response, status = Story.group_stories([first_story.id, second_story.id])
    assert status == 200, response

    grouped_story = Story.get(first_story.id)
    assert grouped_story is not None
    assert grouped_story.relevance_source == 5
    assert grouped_story.relevance == 5
    assert len(grouped_story.news_items) == 2


@pytest.mark.usefixtures("app")
def test_grouping_conflicting_votes_clears_feedback(session):
    admin = User.find_by_name("admin")
    assert admin is not None

    first_story = _create_story([_news_item_payload("manual")], title="Vote merge target")
    second_story = _create_story([_news_item_payload("manual")], title="Vote merge source")

    Story.update(first_story.id, {"vote": "like"}, user=admin)
    Story.update(second_story.id, {"vote": "dislike"}, user=admin)

    response, status = Story.group_stories([first_story.id, second_story.id], user=admin)
    assert status == 200, response

    grouped_story = Story.get(first_story.id)
    assert grouped_story is not None
    assert grouped_story.likes == 0
    assert grouped_story.dislikes == 0
    assert grouped_story.relevance_feedback == 0


@pytest.mark.usefixtures("app")
def test_grouping_matching_votes_dedupes_feedback(session):
    admin = User.find_by_name("admin")
    assert admin is not None

    first_story = _create_story([_news_item_payload("manual")], title="Matching vote target")
    second_story = _create_story([_news_item_payload("manual")], title="Matching vote source")

    Story.update(first_story.id, {"vote": "like"}, user=admin)
    Story.update(second_story.id, {"vote": "like"}, user=admin)

    response, status = Story.group_stories([first_story.id, second_story.id], user=admin)
    assert status == 200, response

    grouped_story = Story.get(first_story.id)
    assert grouped_story is not None
    assert grouped_story.likes == 1
    assert grouped_story.dislikes == 0
    assert grouped_story.relevance_feedback == 1


@pytest.mark.usefixtures("app")
def test_partial_ungroup_keeps_original_feedback_and_new_story_starts_clean(session):
    source = _create_source(rank=4)
    story = _create_story(
        [
            _news_item_payload(source.id, title="Primary grouped item"),
            _news_item_payload(source.id, title="Secondary grouped item"),
        ],
        title="Ungroup feedback story",
    )

    response, status = Story.update(story.id, {"important": True})
    assert status == 200, response

    news_item_to_split = story.news_items[1].id
    admin = User.find_by_name("admin")
    assert admin is not None
    response, status = Story.ungroup_news_items_from_story([news_item_to_split], user=admin)
    assert status == 200, response

    original_story = Story.get(story.id)
    assert original_story is not None
    assert original_story.relevance == 7
    assert original_story.relevance_feedback == 3

    new_story = Story.get(response["new_stories_ids"][0])
    assert new_story is not None
    assert new_story.relevance == 4
    assert new_story.important is False
    assert new_story.relevance_override == 0
    assert new_story.relevance_feedback == 0
