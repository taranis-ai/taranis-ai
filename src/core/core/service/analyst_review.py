from typing import Any

from models.assess import AnalystReviewActionPayload

from core.log import logger
from core.managers.db_manager import db
from core.model.report_item import ReportItem
from core.model.story import Story
from core.model.user import User
from core.service.report_story_sync import ReportStorySyncService


class AnalystReviewService:
    @classmethod
    def triage(cls, payload: AnalystReviewActionPayload, user: User) -> tuple[dict[str, Any], int]:
        story_query = db.select(Story).filter(Story.id == payload.story_id)
        story_query = Story._add_ACL_check(story_query, user)
        story_query = Story._add_TLP_check(story_query, user)
        story = db.session.execute(story_query).scalar()
        if not story:
            return {"error": "Story not found"}, 404

        report = None
        story_attached = False
        if payload.action == "add":
            report, error, status = ReportItem.get_report_item_and_check_permission(payload.report_id or "", user)
            if error or not report:
                return error, status

        try:
            if report and story not in report.stories:
                report.stories.append(story)
                ReportStorySyncService.sync_report_membership(report, [story], "attach")
                story_attached = True

            story.read = True
            story.important = False
            story.last_change = Story.last_change_for_user(user) or story.last_change
            story.update_timestamps()
            story.recompute_relevance()
            story.record_revision(user, note=f"analyst_review_{payload.action}")
            if report and story_attached:
                report.record_revision(user, note="analyst_review_add")
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Failed to apply analyst review action for story %s", payload.story_id)
            return {"error": "Failed to apply analyst review action"}, 500

        try:
            ReportStorySyncService.refresh_auto_update_jobs([story])
        except Exception:
            logger.exception("Failed to refresh MISP auto-update after analyst review for story %s", payload.story_id)

        return {
            "message": "Story added to report" if payload.action == "add" else "Story dismissed",
            "story_id": story.id,
            "report_id": report.id if report else None,
        }, 200
