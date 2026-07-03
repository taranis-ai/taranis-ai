from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Literal

from sqlalchemy import inspect

from core.managers.db_manager import db
from core.service.news_item_tag import NewsItemTagService


if TYPE_CHECKING:
    from core.model.report_item import ReportItem
    from core.model.story import Story


ReportStoryAction = Literal["attach", "detach", "retag"]


class ReportStorySyncService:
    @classmethod
    def retag_story_from_membership(cls, story: "Story") -> "Story | None":
        from core.model.report_item import ReportItem

        state = inspect(story)
        if state.deleted:
            return None

        story.tags = [tag for tag in story.tags if not tag.tag_type.startswith("report_")]
        reports = db.session.execute(db.select(ReportItem).where(ReportItem.stories.any(id=story.id))).scalars().all()
        for report in reports:
            NewsItemTagService.add_report_tag(story, report)
        return story

    @classmethod
    def retag_stories_from_membership(cls, stories: Iterable["Story"]) -> list["Story"]:
        retagged: list["Story"] = []
        for story in stories:
            if updated_story := cls.retag_story_from_membership(story):
                retagged.append(updated_story)
        return retagged

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
