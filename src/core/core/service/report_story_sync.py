from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal

from core.managers.db_manager import db
from core.model.attribute import AttributeType
from core.service.misp_auto_update import refresh_misp_auto_update_jobs
from core.service.story import StoryService


if TYPE_CHECKING:
    from core.model.report_item import ReportItem
    from core.model.story import Story


ReportStoryAction = Literal["attach", "detach", "retag"]


class ReportStorySyncService:
    @staticmethod
    def refresh_auto_update_jobs(stories: Iterable[Story]) -> None:
        refresh_misp_auto_update_jobs(story.id for story in stories)

    @classmethod
    def update_affected_stories(cls, stories: Iterable[Story], flush: bool = True) -> list[Story]:
        stories = list(stories)
        if not stories:
            return []

        if flush:
            db.session.flush()

        for story in stories:
            story.recompute_relevance()

        return stories

    @classmethod
    def _clear_detached_story_attributes(cls, report: ReportItem, stories: Iterable[Story]) -> None:
        detached_story_ids = {story.id for story in stories if story.id}
        if not detached_story_ids:
            return

        for attribute in report.attributes or []:
            if attribute.attribute_type != AttributeType.STORY or not attribute.value:
                continue
            current_ids = [story_id.strip() for story_id in str(attribute.value).split(",") if story_id and story_id.strip()]
            if not any(story_id in detached_story_ids for story_id in current_ids):
                continue
            remaining_ids = [story_id for story_id in current_ids if story_id not in detached_story_ids]
            attribute.value = ",".join(remaining_ids)

    @classmethod
    def sync_report_membership(cls, report: ReportItem, stories: Iterable[Story], action: ReportStoryAction) -> list[Story]:
        stories = list(stories)
        if not stories:
            return []

        if action == "attach":
            for story in stories:
                StoryService.add_report_attribute(story, report)
            cls.update_affected_stories(stories)
            return stories

        if action == "detach":
            cls._clear_detached_story_attributes(report, stories)
            for story in stories:
                StoryService.remove_report_attribute(story, report.id)
            cls.update_affected_stories(stories)
            return stories

        if action == "retag":
            for story in stories:
                StoryService.remove_report_attribute(story, report.id)
                StoryService.add_report_attribute(story, report)
            return stories

        raise ValueError(f"Unsupported report story sync action: {action}")
