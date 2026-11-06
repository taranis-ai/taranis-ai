import pytest

from core.managers.db_manager import db
from core.model.report_item import ReportItem
from core.model.revision import ReportRevision
from core.model.story import Story
from core.model.user import User
from tests.application.support.builders import create_report, create_story


# Issue #1236: ungrouping news items must not silently drop a story from a report.


def _admin() -> User:
    admin = User.find_by_name("admin")
    assert admin is not None
    return admin


def _story(news_item_factory, story_factory, title: str, item_count: int = 1) -> Story:
    return create_story(story_factory([news_item_factory("manual") for _ in range(item_count)], title=title))


def _report_with_stories(report_factory, stories: list[Story]) -> ReportItem:
    report = create_report(report_factory())
    response, status = ReportItem.add_stories(report.id, [story.id for story in stories], _admin())
    assert status == 200, response
    return report


def _reload_report(report_id: str) -> ReportItem:
    db.session.expire_all()
    report = ReportItem.get(report_id)
    assert report is not None
    return report


def _report_story_ids(report_id: str) -> list[str]:
    return [story.id for story in _reload_report(report_id).stories]


def _report_revision_notes(report_id: str) -> list[str | None]:
    query = db.select(ReportRevision.note).filter_by(report_item_id=report_id).order_by(ReportRevision.revision.asc())
    return list(db.session.execute(query).scalars())


def _news_item_ids(story_id: str) -> list[str]:
    db.session.expire_all()
    story = Story.get(story_id)
    assert story is not None
    return sorted(item.id for item in story.news_items)


@pytest.mark.usefixtures("app")
def test_ungroup_endpoint_rejects_emptying_report_story(
    client,
    auth_header,
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    report_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Report story", item_count=2)
    report = _report_with_stories(story_relevance_report_payload_factory, [report_story])
    item_ids = _news_item_ids(report_story.id)
    notes_before = _report_revision_notes(report.id)

    response = client.put("/api/assess/news-items/ungroup", json=item_ids, headers=auth_header)

    assert response.status_code == 400, response.json
    assert response.json == {"error": "Story is assigned to a report"}
    assert _report_story_ids(report.id) == [report_story.id]
    assert _news_item_ids(report_story.id) == item_ids
    assert _report_revision_notes(report.id) == notes_before


@pytest.mark.usefixtures("app")
def test_mixed_request_emptying_report_story_changes_nothing(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    report_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Report story")
    other_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Other story", item_count=2)
    report = _report_with_stories(story_relevance_report_payload_factory, [report_story])
    other_item_ids = _news_item_ids(other_story.id)
    report_item_ids = _news_item_ids(report_story.id)

    # The unrelated story comes first, so a check inside the mutation loop would already have changed it.
    response, status = Story.ungroup_news_items_from_story([other_item_ids[0], *report_item_ids], user=_admin())

    assert status == 400, response
    assert _news_item_ids(other_story.id) == other_item_ids
    assert _news_item_ids(report_story.id) == report_item_ids
    assert _report_story_ids(report.id) == [report_story.id]


@pytest.mark.usefixtures("app")
def test_partial_ungroup_keeps_report_stories_and_records_one_revision(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    story_a = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Story A", item_count=2)
    story_b = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Story B", item_count=2)
    report = _report_with_stories(story_relevance_report_payload_factory, [story_a, story_b])
    items_a = _news_item_ids(story_a.id)
    items_b = _news_item_ids(story_b.id)
    notes_before = _report_revision_notes(report.id)

    response, status = Story.ungroup_news_items_from_story([items_a[0], items_b[0]], user=_admin())

    assert status == 200, response
    assert sorted(_report_story_ids(report.id)) == sorted([story_a.id, story_b.id])
    assert _news_item_ids(story_a.id) == [items_a[1]]
    assert _news_item_ids(story_b.id) == [items_b[1]]
    assert not set(response["new_stories_ids"]) & set(_report_story_ids(report.id))
    assert _report_revision_notes(report.id) == [*notes_before, "ungroup_news_items"]
