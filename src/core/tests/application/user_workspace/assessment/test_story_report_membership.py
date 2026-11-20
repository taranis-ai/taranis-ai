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


@pytest.mark.parametrize(
    ("method", "path", "header_fixture", "api_module", "multiple"),
    [
        ("put", "/api/assess/stories/group", "auth_header", "core.api.assess", False),
        ("post", "/api/assess/stories/group", "auth_header", "core.api.assess", False),
        ("put", "/api/bots/stories/group", "api_header", "core.api.bots", False),
        ("put", "/api/bots/stories/group-multiple", "api_header", "core.api.bots", True),
    ],
    ids=["assess-put", "assess-post", "bot-group", "bot-group-multiple"],
)
def test_grouping_endpoints_invalidate_report_views(
    request,
    session,
    client,
    monkeypatch,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
    method,
    path,
    header_fixture,
    api_module,
    multiple,
):
    report_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Report story")
    other_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Other story")
    report = _report_with_stories(story_relevance_report_payload_factory, [report_story])
    invalidations = []

    def capture_invalidation(status, **kwargs):
        invalidations.append((status, kwargs))

    monkeypatch.setattr(f"{api_module}.invalidate_frontend_cache_on_success", capture_invalidation)
    story_ids = [other_story.id, report_story.id]

    response = getattr(client, method)(
        path,
        json=[story_ids] if multiple else story_ids,
        headers=request.getfixturevalue(header_fixture),
    )

    assert response.status_code == 200, response.get_json()
    assert _report_story_ids(report.id) == [other_story.id]
    assert invalidations == [(200, {"scopes": ("story_views", "report_views")})]


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


@pytest.mark.usefixtures("app")
def test_grouping_recomputes_report_story_tlp_and_records_revision(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    from core.model.news_item_attribute import NewsItemAttribute

    clear_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Clear report story")
    red_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Red story")
    red_story.news_items[0].upsert_attribute(NewsItemAttribute(key="TLP", value="red"))
    red_story.update_status()
    db.session.commit()
    assert clear_story.tlp_level.value == "clear"
    assert red_story.tlp_level.value == "red"
    report = _report_with_stories(story_relevance_report_payload_factory, [clear_story])

    response, status = Story.group_stories([clear_story.id, red_story.id], user=_admin())
    assert status == 200, response

    assert _reload_report(report.id).stories[0].tlp_level.value == "red"
    query = db.select(ReportRevision).filter_by(report_item_id=report.id).order_by(ReportRevision.revision.desc())
    latest = db.session.execute(query).scalars().first()
    assert latest is not None
    assert latest.note == "group_stories"
    # Report payloads embed only id, title and links of stories (#1290), so the snapshot carries no TLP.
    assert any(story["id"] == clear_story.id for story in latest.data["stories"])


@pytest.mark.parametrize("target_already_selected", [False, True], ids=["target-not-selected", "target-already-selected"])
@pytest.mark.usefixtures("app")
def test_grouping_points_story_attribute_selection_to_surviving_story(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    target_already_selected,
):
    from uuid import uuid4

    from core.model.attribute import Attribute, AttributeType
    from core.model.report_item_type import ReportItemType

    absorbed_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Absorbed story")
    target_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Target story")
    other_story = _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, "Other story")
    selected = [absorbed_story, target_story] if target_already_selected else [absorbed_story, other_story]

    suffix = uuid4().hex
    story_attr_def = Attribute(name=f"story_ref_{suffix}", description="Referenced stories attribute", attribute_type=AttributeType.STORY)
    db.session.add(story_attr_def)
    db.session.flush()
    report_type = ReportItemType(
        title=f"Grouping Attribute Report Type {suffix}",
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

    report_id = str(uuid4())
    report, status = ReportItem.add(
        {
            "id": report_id,
            "title": f"Grouping Attribute Report {suffix}",
            "completed": False,
            "report_item_type_id": report_type.id,
            "stories": [story.id for story in selected],
        },
        _admin(),
    )
    assert status == 200

    try:
        story_attr = next(attr for attr in report.attributes if attr.attribute_type == AttributeType.STORY)
        _, update_status = ReportItem.update_report_item(
            report_id, {"attributes": {story_attr.id: ",".join(story.id for story in selected)}}, _admin()
        )
        assert update_status == 200

        response, status = Story.group_stories([target_story.id, absorbed_story.id], user=_admin())
        assert status == 200, response

        expected_ids = [target_story.id] if target_already_selected else [target_story.id, other_story.id]
        reloaded = _reload_report(report_id)
        story_attr_after = next(attr for attr in reloaded.attributes if attr.attribute_type == AttributeType.STORY)
        assert story_attr_after.value == ",".join(expected_ids)
        assert reloaded.to_detail_dict()["used_story_ids"] == expected_ids

        query = db.select(ReportRevision).filter_by(report_item_id=report_id).order_by(ReportRevision.revision.desc())
        latest_revision = db.session.execute(query).scalars().first()
        assert latest_revision is not None
        assert latest_revision.note == "group_stories"
        assert latest_revision.data["used_story_ids"] == expected_ids
    finally:
        if ReportItem.get(report_id):
            ReportItem.delete(report_id)
        if ReportItemType.get(report_type.id):
            db.session.delete(ReportItemType.get(report_type.id))
        if Attribute.get(story_attr_def.id):
            db.session.delete(Attribute.get(story_attr_def.id))
        db.session.commit()


@pytest.mark.usefixtures("app")
def test_locked_report_lookup_matches_report_lookup(
    session,
    story_relevance_news_item_payload_factory,
    story_relevance_story_payload_factory,
    story_relevance_report_payload_factory,
):
    first, second, other = (
        _story(story_relevance_news_item_payload_factory, story_relevance_story_payload_factory, title)
        for title in ("First", "Second", "Other")
    )
    both = _report_with_stories(story_relevance_report_payload_factory, [first, second])
    only_second = _report_with_stories(story_relevance_report_payload_factory, [second])
    _report_with_stories(story_relevance_report_payload_factory, [other])
    _report_with_stories(story_relevance_report_payload_factory, [])

    expected = sorted([both.id, only_second.id])
    assert [report.id for report in ReportItem.get_for_stories([first.id, second.id])] == expected
    assert [report.id for report in ReportItem.lock_for_stories([first.id, second.id])] == expected
    assert ReportItem.lock_for_stories([]) == []
