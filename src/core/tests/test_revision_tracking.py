from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.report_item import ReportItem
from core.model.revision import ReportRevision, StoryRevision
from core.model.story import Story
from core.model.user import User


def _news_item_payload() -> dict:
    now = datetime.utcnow().replace(microsecond=0).isoformat()
    title = f"News Item {uuid.uuid4()}"
    content = f"content-{uuid.uuid4()}"
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "content": content,
        "source": "unit-test",
        "link": "https://example.invalid/story",
        "osint_source_id": "manual",
        "hash": NewsItem.get_hash(title=title, content=content),
        "collected": now,
        "published": now,
    }


def _create_story() -> Story:
    payload = {
        "title": f"Story {uuid.uuid4()}",
        "description": "initial desc",
        "news_items": [_news_item_payload()],
    }
    result, status = Story.add(payload)
    assert status == 200
    return Story.get(result["story_id"])


def _fetch_story_revisions(story_id: str) -> list[StoryRevision]:
    query = db.select(StoryRevision).filter_by(story_id=story_id).order_by(StoryRevision.revision.asc())
    return list(db.session.execute(query).scalars())


def _fetch_report_revisions(report_id: str) -> list[ReportRevision]:
    query = db.select(ReportRevision).filter_by(report_item_id=report_id).order_by(ReportRevision.revision.asc())
    return list(db.session.execute(query).scalars())


@pytest.mark.usefixtures("session")
def test_story_revisions_are_created_on_updates():
    user = User.find_by_name("admin")
    story = _create_story()
    original_title = story.title
    assert story.revision == 0

    Story.update(story.id, {"title": "Updated Title"}, user)
    db.session.refresh(story)
    revisions = _fetch_story_revisions(story.id)
    # Expect 2 revisions: initial (legacy) + update
    assert len(revisions) == 2
    assert story.revision == 2
    # Check initial revision (first in list, revision 1)
    assert revisions[0].revision == 1
    assert revisions[0].data["title"] == original_title
    assert revisions[0].note == "initial"
    # Check update revision (second in list, revision 2)
    assert revisions[1].revision == 2
    assert revisions[1].data["title"] == "Updated Title"
    assert revisions[1].note == "update"
    assert revisions[1].created_by_id == user.id

    Story.update(story.id, {"description": "Changed description"}, user)
    db.session.refresh(story)
    revisions = _fetch_story_revisions(story.id)
    assert len(revisions) == 3
    assert story.revision == 3
    assert revisions[-1].revision == 3
    assert revisions[-1].data["description"] == "Changed description"
    assert revisions[-1].note == "update"
    assert revisions[-1].created_by_id == user.id


@pytest.mark.usefixtures("session")
def test_report_item_revisions_cover_create_and_update(sample_report_type):
    user = User.find_by_name("admin")
    payload = {
        "title": "Initial Report",
        "completed": False,
        "report_item_type_id": sample_report_type.id,
        "stories": [],
    }
    report_item, status = ReportItem.add(payload, user)
    assert status == 200
    assert report_item.revision == 1

    revisions = _fetch_report_revisions(report_item.id)
    assert len(revisions) == 1
    assert revisions[0].revision == 1
    assert revisions[0].data["title"] == "Initial Report"
    assert revisions[0].note == "created"
    assert revisions[0].created_by_id == user.id

    ReportItem.update_report_item(report_item.id, {"title": "Updated Report"}, user)
    db.session.refresh(report_item)
    revisions = _fetch_report_revisions(report_item.id)
    assert len(revisions) == 2
    assert report_item.revision == 2
    assert revisions[-1].revision == 2
    assert revisions[-1].data["title"] == "Updated Report"
    assert revisions[-1].note == "update"


@pytest.mark.usefixtures("session")
def test_story_revision_uses_database_parent_value_when_instance_is_stale():
    user = User.find_by_name("admin")
    story = _create_story()

    db.session.execute(db.text("UPDATE story SET revision = 5 WHERE id = :story_id"), {"story_id": story.id})
    story.record_revision(user, note="stale-sync")
    db.session.flush()

    db.session.refresh(story)
    revisions = _fetch_story_revisions(story.id)
    assert story.revision == 6
    assert revisions[-1].revision == 6
    assert revisions[-1].note == "stale-sync"


@pytest.mark.usefixtures("session")
def test_report_revision_uses_database_parent_value_when_instance_is_stale(sample_report_type):
    user = User.find_by_name("admin")
    payload = {
        "title": "Initial Report",
        "completed": False,
        "report_item_type_id": sample_report_type.id,
        "stories": [],
    }
    report_item, status = ReportItem.add(payload, user)
    assert status == 200

    db.session.execute(db.text("UPDATE report_item SET revision = 5 WHERE id = :report_id"), {"report_id": report_item.id})
    report_item.record_revision(user, note="stale-sync")
    db.session.flush()

    db.session.refresh(report_item)
    revisions = _fetch_report_revisions(report_item.id)
    assert report_item.revision == 6
    assert revisions[-1].revision == 6
    assert revisions[-1].note == "stale-sync"


@pytest.mark.usefixtures("session")
def test_story_update_votes_before_single_commit(monkeypatch):
    user = User.find_by_name("admin")
    story = _create_story()
    story.revision = 1
    db.session.flush()
    events: list[str] = []

    original_record_revision = Story.record_revision

    def record_revision_spy(self, *args, **kwargs):
        events.append("record_revision")
        return original_record_revision(self, *args, **kwargs)

    def commit_spy():
        events.append("commit")
        raise RuntimeError("stop-after-commit")

    monkeypatch.setattr(Story, "record_revision", record_revision_spy)
    monkeypatch.setattr(db.session, "commit", commit_spy)

    with pytest.raises(RuntimeError, match="stop-after-commit"):
        Story.update(story.id, {"vote": "like", "title": "Updated Title"}, user)

    assert events == ["record_revision", "commit"]


@pytest.mark.usefixtures("session")
def test_story_update_attributes_before_single_commit(monkeypatch):
    user = User.find_by_name("admin")
    story = _create_story()
    story.revision = 1
    db.session.flush()
    events: list[str] = []

    original_record_revision = Story.record_revision

    def record_revision_spy(self, *args, **kwargs):
        events.append("record_revision")
        return original_record_revision(self, *args, **kwargs)

    def commit_spy():
        events.append("commit")
        raise RuntimeError("stop-after-commit")

    monkeypatch.setattr(Story, "record_revision", record_revision_spy)
    monkeypatch.setattr(db.session, "commit", commit_spy)

    with pytest.raises(RuntimeError, match="stop-after-commit"):
        Story.update(story.id, {"attributes": [{"key": "threat_actor", "value": "APT29"}]}, user)

    assert events == ["record_revision", "commit"]
