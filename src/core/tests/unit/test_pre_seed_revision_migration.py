from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from core.model.news_item import NewsItem
from core.model.report_item import ReportItem
from core.model.revision import ReportRevision, StoryRevision
from core.model.story import Story


def _news_item_payload() -> dict:
    now = datetime.utcnow().replace(microsecond=0).isoformat()
    title = f"Seed News Item {uuid.uuid4()}"
    content = f"content-{uuid.uuid4()}"
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "content": content,
        "source": "seed-test",
        "link": "https://example.invalid/seed-test",
        "osint_source_id": "manual",
        "hash": NewsItem.get_hash(title=title, content=content),
        "collected": now,
        "published": now,
    }


def _create_story() -> Story:
    payload = {
        "title": f"Seed Story {uuid.uuid4()}",
        "description": "seed story",
        "news_items": [_news_item_payload()],
    }
    result, status = Story.add(payload)
    assert status == 200
    return Story.get(result["story_id"])


def _create_report(sample_report_type) -> ReportItem:
    payload = {
        "title": f"Seed Report {uuid.uuid4()}",
        "completed": False,
        "report_item_type_id": sample_report_type.id,
        "stories": [],
    }
    report, status = ReportItem.add(payload)
    assert status == 200
    return ReportItem.get(report.id)


@pytest.mark.usefixtures("app")
def test_pre_seed_update_backfills_missing_story_and_report_revisions(session, sample_report_type):
    from core.managers.db_manager import db
    from core.managers.db_seed_manager import pre_seed_update

    legacy_story = _create_story()
    current_story = _create_story()
    legacy_report = _create_report(sample_report_type)
    current_report = _create_report(sample_report_type)

    db.session.execute(db.delete(StoryRevision).where(StoryRevision.story_id == legacy_story.id))
    db.session.execute(db.text("UPDATE story SET revision = -1 WHERE id = :story_id"), {"story_id": legacy_story.id})
    db.session.execute(db.delete(ReportRevision).where(ReportRevision.report_item_id == legacy_report.id))
    db.session.execute(db.text("UPDATE report_item SET revision = -1 WHERE id = :report_id"), {"report_id": legacy_report.id})
    db.session.commit()

    pre_seed_update(db.engine)

    db.session.expire_all()

    legacy_story = Story.get(legacy_story.id)
    current_story = Story.get(current_story.id)
    legacy_report = ReportItem.get(legacy_report.id)
    current_report = ReportItem.get(current_report.id)

    legacy_story_revisions = list(
        db.session.execute(db.select(StoryRevision).filter_by(story_id=legacy_story.id).order_by(StoryRevision.revision.asc())).scalars()
    )
    current_story_revisions = list(
        db.session.execute(db.select(StoryRevision).filter_by(story_id=current_story.id).order_by(StoryRevision.revision.asc())).scalars()
    )
    legacy_report_revisions = list(
        db.session.execute(
            db.select(ReportRevision).filter_by(report_item_id=legacy_report.id).order_by(ReportRevision.revision.asc())
        ).scalars()
    )
    current_report_revisions = list(
        db.session.execute(
            db.select(ReportRevision).filter_by(report_item_id=current_report.id).order_by(ReportRevision.revision.asc())
        ).scalars()
    )

    assert legacy_story is not None
    assert legacy_story.revision == 1
    assert [revision.note for revision in legacy_story_revisions] == ["initial"]

    assert current_story is not None
    assert current_story.revision == 1
    assert [revision.note for revision in current_story_revisions] == ["created"]

    assert legacy_report is not None
    assert legacy_report.revision == 1
    assert [revision.note for revision in legacy_report_revisions] == ["initial"]

    assert current_report is not None
    assert current_report.revision == 1
    assert [revision.note for revision in current_report_revisions] == ["created"]
