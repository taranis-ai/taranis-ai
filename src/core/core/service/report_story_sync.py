from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Literal

from core.managers.db_manager import db
from core.service.news_item_tag import NewsItemTagService


if TYPE_CHECKING:
    from core.model.report_item import ReportItem
    from core.model.story import Story


ReportStoryAction = Literal["attach", "detach", "retag"]


class ReportStorySyncService:
    @staticmethod
    def _unique_stories(stories: Iterable["Story"]) -> list["Story"]:
        unique_stories: dict[str, Story] = {}
        for story in stories:
            if story is None or not getattr(story, "id", None):
                continue
            unique_stories[story.id] = story
        return list(unique_stories.values())

    @classmethod
    def update_affected_stories(cls, stories: Iterable["Story"], flush: bool = True) -> list["Story"]:
        unique_stories = cls._unique_stories(stories)
        if not unique_stories:
            return []

        if flush:
            db.session.flush()

        for story in unique_stories:
            story.recompute_relevance()

        return unique_stories

    @classmethod
    def sync_report_membership(cls, report: "ReportItem", stories: Iterable["Story"], action: ReportStoryAction) -> list["Story"]:
        unique_stories = cls._unique_stories(stories)
        if not unique_stories:
            return []

        if action == "attach":
            for story in unique_stories:
                NewsItemTagService.add_report_tag(story, report)
            cls.update_affected_stories(unique_stories)
            return unique_stories

        if action == "detach":
            for story in unique_stories:
                NewsItemTagService.remove_report_tag(story, report.id)
            cls.update_affected_stories(unique_stories)
            return unique_stories

        if action == "retag":
            for story in unique_stories:
                NewsItemTagService.remove_report_tag(story, report.id)
                NewsItemTagService.add_report_tag(story, report)
            return unique_stories

        raise ValueError(f"Unsupported report story sync action: {action}")
