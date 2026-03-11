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
from core.service.news_item import NewsItemService
from core.service.news_item_tag import NewsItemTagService


def _news_item_payload(source: str = "unit-test") -> dict:
    now = datetime.utcnow().replace(microsecond=0).isoformat()
    title = f"News Item {uuid.uuid4()}"
    content = f"content-{uuid.uuid4()}"
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "content": content,
        "source": source,
        "link": "https://example.invalid/story",
        "osint_source_id": "manual",
        "hash": NewsItem.get_hash(title=title, content=content),
        "collected": now,
        "published": now,
    }


def _create_story(news_item_count: int = 1) -> Story:
    payload = {
        "title": f"Story {uuid.uuid4()}",
        "description": "initial desc",
        "news_items": [_news_item_payload() for _ in range(news_item_count)],
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

    Story.update(story.id, {"title": "Updated Title"}, user)
    db.session.refresh(story)
    revisions = _fetch_story_revisions(story.id)
    assert len(revisions) == 2
    assert story.revision == 2
    assert revisions[0].revision == 1
    assert revisions[0].note == "created"
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
def test_story_set_tags_creates_created_and_update_revisions():
    story = _create_story()

    response, status = story.set_tags(["apt29"])

    assert status == 200
    assert response["message"].startswith("Successfully updated story")
    db.session.refresh(story)
    revisions = _fetch_story_revisions(story.id)
    assert story.revision == 2
    assert [revision.note for revision in revisions] == ["created", "set_tags"]


@pytest.mark.usefixtures("session")
def test_news_item_service_update_creates_story_revisions():
    user = User.find_by_name("admin")
    payload = {
        "title": f"Story {uuid.uuid4()}",
        "description": "initial desc",
        "news_items": [_news_item_payload(source="manual")],
    }
    result, status = Story.add(payload)
    assert status == 200
    story = Story.get(result["story_id"])
    news_item = story.news_items[0]

    response, status = NewsItemService.update(news_item.id, {"title": "Updated News Item"}, user)

    assert status == 200
    assert response["story_id"] == story.id
    db.session.refresh(story)
    revisions = _fetch_story_revisions(story.id)
    assert story.revision == 2
    assert [revision.note for revision in revisions] == ["created", "update_news_item"]
    assert revisions[-1].data["news_items"][0]["title"] == "Updated News Item"


@pytest.mark.usefixtures("session")
def test_news_item_attribute_update_creates_story_revisions():
    story = _create_story()
    news_item = story.news_items[0]

    response, status = NewsItem.update_attributes(news_item.id, [{"key": "threat_actor", "value": "APT29"}])

    assert status == 200
    assert "updated" in response["message"]
    db.session.refresh(story)
    revisions = _fetch_story_revisions(story.id)
    assert story.revision == 2
    assert [revision.note for revision in revisions] == ["created", "update_news_item_attributes"]


@pytest.mark.usefixtures("session")
def test_story_creation_creates_created_revision():
    story = _create_story()

    revisions = _fetch_story_revisions(story.id)

    assert story.revision == 1
    assert len(revisions) == 1
    assert revisions[0].revision == 1
    assert revisions[0].note == "created"


@pytest.mark.usefixtures("session")
def test_story_creation_handles_mixed_timezone_published_dates():
    aware_published = datetime.fromisoformat("2024-01-01T00:30:00+02:00")
    expected_created = datetime.fromisoformat("2023-12-31T22:30:00")
    payload = {
        "title": f"Story {uuid.uuid4()}",
        "news_items": [
            _news_item_payload(),
            {
                **_news_item_payload(),
                "published": aware_published.isoformat(),
            },
        ],
    }
    payload["news_items"][0]["published"] = "2024-01-01T00:00:00"

    result, status = Story.add(payload)

    assert status == 200
    story = Story.get(result["story_id"])
    assert story is not None
    assert story.created == expected_created
    assert story.to_dict()["created"] == "2023-12-31T22:30:00+00:00"
    assert any(news_item.published == expected_created for news_item in story.news_items)


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
def test_report_add_stories_creates_created_and_update_revisions(sample_report_type):
    user = User.find_by_name("admin")
    payload = {
        "title": "Initial Report",
        "completed": False,
        "report_item_type_id": sample_report_type.id,
        "stories": [],
    }
    report_item, status = ReportItem.add(payload, user)
    assert status == 200
    story = _create_story()

    response, status = ReportItem.add_stories(report_item.id, [story.id], user)

    assert status == 200
    assert response["message"].startswith("Successfully added")
    db.session.refresh(report_item)
    revisions = _fetch_report_revisions(report_item.id)
    assert report_item.revision == 2
    assert [revision.note for revision in revisions] == ["created", "add_stories"]


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


@pytest.mark.usefixtures("session")
def test_report_title_retag_happens_before_revision_and_commit(sample_report_type, monkeypatch):
    user = User.find_by_name("admin")
    story = _create_story()
    payload = {
        "title": "Initial Report",
        "completed": False,
        "report_item_type_id": sample_report_type.id,
        "stories": [story.id],
    }
    report_item, status = ReportItem.add(payload, user)
    assert status == 200
    events: list[str] = []

    original_record_revision = ReportItem.record_revision

    def remove_tag_spy(*args, **kwargs):
        events.append("remove_report_tag")

    def add_tag_spy(*args, **kwargs):
        events.append("add_report_tag")

    def record_revision_spy(self, *args, **kwargs):
        events.append("record_revision")
        return original_record_revision(self, *args, **kwargs)

    def commit_spy():
        events.append("commit")
        raise RuntimeError("stop-after-commit")

    monkeypatch.setattr(NewsItemTagService, "remove_report_tag", remove_tag_spy)
    monkeypatch.setattr(NewsItemTagService, "add_report_tag", add_tag_spy)
    monkeypatch.setattr(ReportItem, "record_revision", record_revision_spy)
    monkeypatch.setattr(db.session, "commit", commit_spy)

    with pytest.raises(RuntimeError, match="stop-after-commit"):
        ReportItem.update_report_item(report_item.id, {"title": "Renamed Report"}, user)

    assert events == ["remove_report_tag", "add_report_tag", "record_revision", "commit"]
