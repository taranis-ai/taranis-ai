from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Literal

from core.managers.db_manager import db
from core.model.attribute import AttributeType
from core.service.misp_auto_update import refresh_misp_auto_update_jobs
from core.service.story import StoryService


if TYPE_CHECKING:
    from core.model.report_item import ReportItem
    from core.model.story import Story
    from core.model.user import User


ReportStoryAction = Literal["attach", "detach", "retag"]


class ReportStorySyncService:
    @staticmethod
    def parse_story_ids(raw_value: Any) -> list[str]:
        if not raw_value:
            return []
        return [story_id.strip() for story_id in str(raw_value).split(",") if story_id and story_id.strip()]

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
            current_ids = cls.parse_story_ids(attribute.value)
            if not any(story_id in detached_story_ids for story_id in current_ids):
                continue
            remaining_ids = [story_id for story_id in current_ids if story_id not in detached_story_ids]
            attribute.value = ",".join(remaining_ids)

    @classmethod
    def _replace_absorbed_story_attributes(cls, report: ReportItem, absorbed_story_ids: set[str], target_story_id: str) -> None:
        """Point STORY attribute selections of absorbed stories to the surviving story, keeping order without duplicates."""
        for attribute in report.attributes or []:
            if attribute.attribute_type != AttributeType.STORY or not attribute.value:
                continue
            current_ids = cls.parse_story_ids(attribute.value)
            if not any(story_id in absorbed_story_ids for story_id in current_ids):
                continue
            replaced_ids = [target_story_id if story_id in absorbed_story_ids else story_id for story_id in current_ids]
            attribute.value = ",".join(dict.fromkeys(replaced_ids))

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

    @classmethod
    def keep_memberships_after_merge(
        cls,
        target_story: Story,
        source_stories: list[Story],
        absorbed_story_ids: list[str],
    ) -> list[ReportItem]:
        """Keep report links when stories are merged and return every report that contains a merged story."""
        if not source_stories:
            return []

        # Local import: core.model.report_item imports this module at module level.
        from core.model.report_item import ReportItem

        story_ids = [target_story.id, *(story.id for story in source_stories)]
        absorbed = set(absorbed_story_ids)
        # The caller has locked the stories; lock the reports before their stories and STORY fields are read.
        reports = ReportItem.lock_for_stories(story_ids)
        for report in reports:
            cls._replace_absorbed_story_attributes(report, absorbed, target_story.id)
            remaining = [story for story in report.stories if story.id not in absorbed]
            if len(remaining) != len(report.stories) and target_story not in remaining:
                report.stories = [*remaining, target_story]
                cls.sync_report_membership(report, [target_story], "attach")
            else:
                report.stories = remaining
        return reports

    @staticmethod
    def record_report_revisions(reports: Iterable[ReportItem], user: User | None, note: str) -> None:
        """Record a revision for each report; call after story status is recomputed so snapshots are current."""
        for report in reports:
            report.record_revision(user, note=note)
