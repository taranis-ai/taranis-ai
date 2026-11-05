from __future__ import annotations

import pytest

from core.managers.db_manager import db
from core.model.report_item import ReportItem
from core.model.revision import ReportRevision
from core.model.story import Story
from core.model.user import User
from tests.application.support.builders import create_report, create_story


# Issue #1177: clustering or moving news items must not silently drop a story from a report.


def _admin() -> User:
    admin = User.find_by_name("admin")
    assert admin is not None
    return admin


def _story(news_item_factory, story_factory, title: str, item_count: int = 1) -> Story:
    return create_story(story_factory([news_item_factory("manual") for _ in range(item_count)], title=title))


def _report_with_stories(report_factory, stories: list[Story], **extra_fields) -> ReportItem:
    report = create_report(report_factory(**extra_fields))
    if stories:
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


@pytest.mark.usefixtures("app")
def test_absorbed_report_story_is_replaced_by_surviving_story(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    report_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Report story")
    other_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Other story")
    report = _report_with_stories(story_relevance_report_payload_factory, [report_story])

    response, status = Story.group_stories([other_story.id, report_story.id], user=_admin())
    assert status == 200, response

    assert _report_story_ids(report.id) == [other_story.id]
    assert len(_reload_report(report.id).stories[0].news_items) == 2
    assert _report_revision_notes(report.id)[-1] == "group_stories"


@pytest.mark.usefixtures("app")
def test_surviving_report_story_stays_and_records_revision(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    report_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Report story")
    other_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Other story")
    report = _report_with_stories(story_relevance_report_payload_factory, [report_story])
    notes_before = _report_revision_notes(report.id)

    response, status = Story.group_stories([report_story.id, other_story.id], user=_admin())
    assert status == 200, response

    assert _report_story_ids(report.id) == [report_story.id]
    assert len(_reload_report(report.id).stories[0].news_items) == 2
    assert _report_revision_notes(report.id) == [*notes_before, "group_stories"]


@pytest.mark.usefixtures("app")
def test_grouping_two_stories_of_same_report_keeps_single_entry(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    first_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "First story")
    second_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Second story")
    report = _report_with_stories(story_relevance_report_payload_factory, [first_story, second_story])

    response, status = Story.group_stories([first_story.id, second_story.id], user=_admin())
    assert status == 200, response

    assert _report_story_ids(report.id) == [first_story.id]
    assert _report_revision_notes(report.id)[-1] == "group_stories"


@pytest.mark.usefixtures("app")
def test_grouping_stories_from_different_reports_links_survivor_to_both(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    first_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "First story")
    second_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Second story")
    first_report = _report_with_stories(story_relevance_report_payload_factory, [first_story])
    second_report = _report_with_stories(story_relevance_report_payload_factory, [second_story])

    response, status = Story.group_stories([first_story.id, second_story.id], user=_admin())
    assert status == 200, response

    assert _report_story_ids(first_report.id) == [first_story.id]
    assert _report_story_ids(second_report.id) == [first_story.id]
    assert _report_revision_notes(first_report.id)[-1] == "group_stories"
    assert _report_revision_notes(second_report.id)[-1] == "group_stories"


@pytest.mark.usefixtures("app")
def test_completed_report_keeps_story_and_status(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    report_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Report story")
    other_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Other story")
    report = _report_with_stories(story_relevance_report_payload_factory, [report_story], completed=True)

    response, status = Story.group_stories([other_story.id, report_story.id], user=_admin())
    assert status == 200, response

    reloaded = _reload_report(report.id)
    assert [story.id for story in reloaded.stories] == [other_story.id]
    # Status handling is out of scope for #1177 and follows with the report lifecycle (#1048).
    assert reloaded.completed is True


@pytest.mark.usefixtures("app")
def test_surviving_story_gets_report_attribute(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    report_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Report story")
    other_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Other story")
    report = _report_with_stories(story_relevance_report_payload_factory, [report_story])

    response, status = Story.group_stories([other_story.id, report_story.id], user=_admin())
    assert status == 200, response

    db.session.expire_all()
    surviving_story = Story.get(other_story.id)
    assert surviving_story is not None
    assert surviving_story.find_attribute_by_key(f"report_{report.id}") is not None


@pytest.mark.usefixtures("app")
def test_partial_move_keeps_report_story_and_records_revision(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    report_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Report story", item_count=2)
    target_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Target story")
    report = _report_with_stories(story_relevance_report_payload_factory, [report_story])
    moved_item_id = report_story.news_items[0].id

    response, status = Story.move_items_to_story(target_story.id, [moved_item_id], user=_admin())
    assert status == 200, response

    reloaded = _reload_report(report.id)
    assert [story.id for story in reloaded.stories] == [report_story.id]
    assert moved_item_id not in {item.id for item in reloaded.stories[0].news_items}
    assert _report_revision_notes(report.id)[-1] == "move_items_to_story"


@pytest.mark.usefixtures("app")
def test_grouping_without_report_stories_leaves_reports_untouched(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    unrelated_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Unrelated report story")
    report = _report_with_stories(story_relevance_report_payload_factory, [unrelated_story])
    notes_before = _report_revision_notes(report.id)
    first_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "First story")
    second_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Second story")

    response, status = Story.group_stories([first_story.id, second_story.id], user=_admin())
    assert status == 200, response

    assert _report_story_ids(report.id) == [unrelated_story.id]
    assert _report_revision_notes(report.id) == notes_before
