from types import SimpleNamespace
from typing import cast

from core.model.attribute import AttributeType
from core.model.report_item import ReportItem
from core.model.story import Story
from core.service.report_story_sync import ReportStorySyncService


def test_detach_cleans_story_attributes_and_preserves_other_selections(monkeypatch):
    removed_from_stories: list[tuple[str, str]] = []
    updated_stories: list[str] = []

    monkeypatch.setattr(
        "core.service.report_story_sync.StoryService.remove_report_attribute",
        lambda story, report_id: removed_from_stories.append((story.id, report_id)),
    )
    monkeypatch.setattr(
        ReportStorySyncService,
        "update_affected_stories",
        classmethod(lambda cls, stories, flush=True: updated_stories.extend(story.id for story in stories) or list(stories)),
    )

    story_multi = SimpleNamespace(attribute_type=AttributeType.STORY, value="story-1,story-2,story-3")
    story_spaced = SimpleNamespace(attribute_type=AttributeType.STORY, value=" story-2 , story-1 ")
    story_unrelated = SimpleNamespace(attribute_type=AttributeType.STORY, value="story-3")
    story_empty = SimpleNamespace(attribute_type=AttributeType.STORY, value="")
    story_none = SimpleNamespace(attribute_type=AttributeType.STORY, value=None)
    non_story = SimpleNamespace(attribute_type=AttributeType.TEXT, value="story-1,story-2")

    report = SimpleNamespace(
        id="report-1",
        attributes=[story_multi, story_spaced, story_unrelated, story_empty, story_none, non_story],
    )
    detached = [SimpleNamespace(id="story-1")]

    result = ReportStorySyncService.sync_report_membership(
        cast(ReportItem, report),
        cast(list[Story], detached),
        "detach",
    )

    assert [story.id for story in result] == ["story-1"]
    assert story_multi.value == "story-2,story-3"
    assert story_spaced.value == "story-2"
    assert story_unrelated.value == "story-3"
    assert story_empty.value == ""
    assert story_none.value is None
    assert non_story.value == "story-1,story-2"
    assert removed_from_stories == [("story-1", "report-1")]
    assert updated_stories == ["story-1"]


def test_detach_clears_last_selected_story_id_to_empty_string(monkeypatch):
    monkeypatch.setattr(
        "core.service.report_story_sync.StoryService.remove_report_attribute",
        lambda _story, _report_id: None,
    )
    monkeypatch.setattr(
        ReportStorySyncService,
        "update_affected_stories",
        classmethod(lambda cls, stories, flush=True: list(stories)),
    )

    story_single = SimpleNamespace(attribute_type=AttributeType.STORY, value="story-1")
    report = SimpleNamespace(id="report-1", attributes=[story_single])
    detached = [SimpleNamespace(id="story-1")]

    ReportStorySyncService.sync_report_membership(
        cast(ReportItem, report),
        cast(list[Story], detached),
        "detach",
    )

    assert story_single.value == ""
