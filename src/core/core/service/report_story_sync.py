from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal

from core.managers.db_manager import db
from core.service.misp_auto_update import refresh_misp_auto_update_jobs
from core.service.story import StoryService


if TYPE_CHECKING:
    from core.model.report_item import ReportItem
    from core.model.story import Story


ReportStoryAction = Literal["attach", "detach", "retag"]


class ReportStorySyncService:
    @staticmethod
    def refresh_auto_update_jobs(stories: Iterable["Story"]) -> None:
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
