from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Literal

from core.managers.db_manager import db
from core.model.story import ReportItemStory
from core.service.misp_auto_update import refresh_misp_auto_update_jobs
from core.service.story import StoryService


if TYPE_CHECKING:
    from core.model.report_item import ReportItem
    from core.model.story import Story
    from core.model.user import User


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

    @classmethod
    def keep_memberships_after_merge(
        cls,
        target_story: Story,
        source_stories: list[Story],
        absorbed_story_ids: list[str],
        user: User | None,
        revision_note: str,
    ) -> None:
        """Keep report links when stories are merged and record a revision in every affected report."""
        if not source_stories:
            return

        # Local import: core.model.report_item imports this module at module level.
        from core.model.report_item import ReportItem

        story_ids = [target_story.id, *(story.id for story in source_stories)]
        query = (
            db.select(ReportItem)
            .join(ReportItemStory, ReportItemStory.report_item_id == ReportItem.id)
            .where(ReportItemStory.story_id.in_(story_ids))
            .distinct()
        )
        absorbed = set(absorbed_story_ids)
        for report in db.session.execute(query).scalars():
            remaining = [story for story in report.stories if story.id not in absorbed]
            if len(remaining) != len(report.stories) and target_story not in remaining:
                report.stories = [*remaining, target_story]
                cls.sync_report_membership(report, [target_story], "attach")
            else:
                report.stories = remaining
            report.record_revision(user, note=revision_note)
