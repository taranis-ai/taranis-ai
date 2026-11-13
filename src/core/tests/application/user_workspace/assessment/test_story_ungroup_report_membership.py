import pytest

from core.managers.db_manager import db
from core.model.report_item import ReportItem
from core.model.revision import ReportRevision
from core.model.story import Story
from core.model.user import User
from tests.application.support.builders import create_report, create_story


# Issue #1236: ungrouping news items must not silently drop a story from a report.

CONFIRM_ERROR = "Ungrouping removes the story from reports"


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
def test_ungroup_endpoint_requires_confirmation_then_detaches_report_story(
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

    assert response.status_code == 409, response.json
    assert response.json == {"error": CONFIRM_ERROR, "reports": [{"id": report.id, "title": report.title}]}
    assert _report_story_ids(report.id) == [report_story.id]
    assert _news_item_ids(report_story.id) == item_ids
    assert _report_revision_notes(report.id) == notes_before

    response = client.put("/api/assess/news-items/ungroup?confirm=true", json=item_ids, headers=auth_header)

    assert response.status_code == 200, response.json
    assert _report_story_ids(report.id) == []
    assert Story.get(report_story.id) is None
    assert len(response.json["new_stories_ids"]) == 2
    assert _report_revision_notes(report.id) == [*notes_before, "ungroup_news_items"]


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

    assert status == 409, response
    assert response["reports"] == [{"id": report.id, "title": report.title}]
    assert _news_item_ids(other_story.id) == other_item_ids
    assert _news_item_ids(report_story.id) == report_item_ids
    assert _report_story_ids(report.id) == [report_story.id]


@pytest.mark.usefixtures("app")
def test_confirmed_ungroup_without_report_write_access_changes_nothing(
    session,
    report_items,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
):
    report_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Report story")
    _, _, report, _ = report_items  # TLP:RED, not writable for the TLP:CLEAR seed user
    response, status = ReportItem.add_stories(report.id, [report_story.id], _admin())
    assert status == 200, response
    user = User.find_by_name("user")
    assert user is not None
    item_ids = _news_item_ids(report_story.id)
    notes_before = _report_revision_notes(report.id)

    response, status = Story.ungroup_news_items_from_story(item_ids, user=user, confirm=True)

    assert status == 403, response
    assert response == {"error": "User is not allowed to update report"}
    assert _news_item_ids(report_story.id) == item_ids
    assert _report_story_ids(report.id) == [report_story.id]
    assert _report_revision_notes(report.id) == notes_before


@pytest.mark.usefixtures("app")
def test_confirmed_ungroup_without_analyze_update_changes_nothing(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    from core.model.permission import Permission
    from core.model.role import Role

    report_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Report story")
    report = _report_with_stories(story_relevance_report_payload_factory, [report_story])
    user = User.find_by_name("user")
    assert user is not None
    assert report.access_allowed(user, True)  # ACL and TLP allow writing, only the role is missing
    user_role = Role.filter_by_name("User")
    assert user_role is not None
    for permission in Permission.get_bulk(["ANALYZE_UPDATE"]):
        user_role.permissions.remove(permission)
    db.session.flush()
    assert "ANALYZE_UPDATE" not in user.get_permissions()
    item_ids = _news_item_ids(report_story.id)
    notes_before = _report_revision_notes(report.id)

    response, status = Story.ungroup_news_items_from_story(item_ids, user=user, confirm=True)

    assert status == 403, response
    assert response == {"error": "User is not allowed to update report"}
    assert _news_item_ids(report_story.id) == item_ids
    assert _report_story_ids(report.id) == [report_story.id]
    assert _report_revision_notes(report.id) == notes_before


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


@pytest.mark.usefixtures("app")
def test_confirmed_ungroup_clears_detached_story_from_report_story_attributes(
    client,
    auth_header,
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
):
    from uuid import uuid4
    from uuid6 import uuid7
    from core.model.attribute import Attribute, AttributeType
    from core.model.report_item_type import ReportItemType

    story_to_ungroup = _story(
        story_relevance_news_item_payload_factory,
        story_relevance_story_payload_factory,
        "Story to ungroup",
        item_count=1,
    )
    story_to_keep = _story(
        story_relevance_news_item_payload_factory,
        story_relevance_story_payload_factory,
        "Story to keep",
        item_count=1,
    )

    suffix = uuid4().hex
    story_attr_def = Attribute(
        name=f"story_ref_{suffix}",
        description="Referenced stories attribute",
        attribute_type=AttributeType.STORY,
    )
    db.session.add(story_attr_def)
    db.session.flush()

    report_type = ReportItemType(
        title=f"Ungroup Attribute Report Type {suffix}",
        description="Report type with STORY attribute",
        attribute_groups=[
            {
                "index": 0,
                "title": "Analysis",
                "description": "Analysis attributes",
                "attribute_group_items": [
                    {
                        "index": 0,
                        "attribute_id": story_attr_def.id,
                        "title": "Referenced Stories",
                        "description": "Referenced stories",
                        "required": False,
                    }
                ],
            }
        ],
    )
    db.session.add(report_type)
    db.session.commit()

    report_id = str(uuid7())
    report, status = ReportItem.add(
        {
            "id": report_id,
            "title": f"Ungroup Attribute Report {suffix}",
            "completed": False,
            "report_item_type_id": report_type.id,
            "stories": [story_to_ungroup.id, story_to_keep.id],
        },
        _admin(),
    )
    assert status == 200

    try:
        story_attr = next(attr for attr in report.attributes if attr.attribute_type == AttributeType.STORY)
        updated, update_status = ReportItem.update_report_item(
            report_id,
            {"attributes": {story_attr.id: f"{story_to_ungroup.id},{story_to_keep.id}"}},
            _admin(),
        )
        assert update_status == 200
        assert updated["used_story_ids"] == [story_to_ungroup.id, story_to_keep.id]

        item_ids = _news_item_ids(story_to_ungroup.id)
        notes_before = _report_revision_notes(report_id)

        response = client.put("/api/assess/news-items/ungroup", json=item_ids, headers=auth_header)
        assert response.status_code == 409
        assert response.json == {"error": CONFIRM_ERROR, "reports": [{"id": report.id, "title": report.title}]}

        response = client.put("/api/assess/news-items/ungroup?confirm=true", json=item_ids, headers=auth_header)
        assert response.status_code == 200

        assert _report_story_ids(report_id) == [story_to_keep.id]
        assert Story.get(story_to_ungroup.id) is None

        reloaded = _reload_report(report_id)
        story_attr_after = next(attr for attr in reloaded.attributes if attr.attribute_type == AttributeType.STORY)
        assert story_attr_after.value == story_to_keep.id
        assert reloaded.to_detail_dict()["used_story_ids"] == [story_to_keep.id]
        assert _report_revision_notes(report_id) == [*notes_before, "ungroup_news_items"]

        latest_revision = db.session.execute(
            db.select(ReportRevision).where(ReportRevision.report_item_id == report_id).order_by(ReportRevision.revision.desc())
        ).scalars().first()
        assert latest_revision is not None
        assert latest_revision.data["used_story_ids"] == [story_to_keep.id]
    finally:
        if ReportItem.get(report_id):
            ReportItem.delete(report_id)
        if ReportItemType.get(report_type.id):
            db.session.delete(ReportItemType.get(report_type.id))
        if Attribute.get(story_attr_def.id):
            db.session.delete(Attribute.get(story_attr_def.id))
        db.session.commit()
