from __future__ import annotations

import pytest

from core.model.report_item import ReportItem
from core.model.revision import ReportRevision, StoryRevision
from core.model.story import Story
from tests.application.support.builders import create_report, create_story


@pytest.mark.usefixtures("app")
def test_pre_seed_update_backfills_missing_story_and_report_revisions(session, seed_story_payload_factory, seed_report_payload_factory):
    from core.managers.db_manager import db
    from core.managers.db_seed_manager import pre_seed_update

    legacy_story = create_story(seed_story_payload_factory())
    current_story = create_story(seed_story_payload_factory())
    legacy_report = create_report(seed_report_payload_factory())
    current_report = create_report(seed_report_payload_factory())

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
