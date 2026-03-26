from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Literal

from core.managers.db_manager import db
from core.service.news_item_tag import NewsItemTagService


if TYPE_CHECKING:
    from core.model.report_item import ReportItem
    from core.model.story import Story


ReportStoryAction = Literal["attach", "detach", "retag"]


class ReportStorySyncService:
    @classmethod
    def update_affected_stories(cls, stories: Iterable["Story"], flush: bool = True) -> list["Story"]:
        stories = list(stories)
        if not stories:
            return []

        if flush:
            db.session.flush()

        for story in stories:
            story.recompute_relevance()

        return stories

    @classmethod
    def sync_report_membership(cls, report: "ReportItem", stories: Iterable["Story"], action: ReportStoryAction) -> list["Story"]:
        stories = list(stories)
        if not stories:
            return []

        if action == "attach":
            for story in stories:
                NewsItemTagService.add_report_tag(story, report)
            cls.update_affected_stories(stories)
            return stories

        if action == "detach":
            for story in stories:
                NewsItemTagService.remove_report_tag(story, report.id)
            cls.update_affected_stories(stories)
            return stories

        if action == "retag":
            for story in stories:
                NewsItemTagService.remove_report_tag(story, report.id)
                NewsItemTagService.add_report_tag(story, report)
            return stories

        raise ValueError(f"Unsupported report story sync action: {action}")
