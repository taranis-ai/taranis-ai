from core.managers import queue_manager
from core.model.news_item import NewsItem
from core.model.news_item_conflict import NewsItemConflict
from core.model.product import Product
from core.model.report_item import ReportItem
from core.model.story import Story
from core.model.story_conflict import StoryConflict
from core.model.task import Task
from core.service.health import get_health_response


class DashboardService:
    @staticmethod
    def _count_user_scheduled_jobs(schedules: dict) -> int:
        if not isinstance(schedules, dict):
            return 0

        if "items" not in schedules:
            return int(schedules.get("total_count", 0) or 0)

        items = schedules.get("items", [])
        if not isinstance(items, list):
            return int(schedules.get("total_count", 0) or 0)

        housekeeping_job_ids = {
            queue_manager.TOKEN_CLEANUP_JOB_ID,
            queue_manager.TASK_RECONCILIATION_JOB_ID,
        }
        return sum(1 for item in items if isinstance(item, dict) and item.get("id") not in housekeeping_job_ids)

    @classmethod
    def get_dashboard_data(cls) -> dict:
        total_news_items = NewsItem.get_count()
        total_story_items = Story.get_count()
        total_products = Product.get_count()
        report_items_completed = ReportItem.count_all(True)
        report_items_in_progress = ReportItem.count_all(False)
        latest_collected = NewsItem.latest_collected()
        schedules, _ = queue_manager.queue_manager.get_scheduled_jobs()
        schedule_length = cls._count_user_scheduled_jobs(schedules)
        conflict_count = len(StoryConflict.conflict_store) + len(NewsItemConflict.conflict_store)
        health_status, _ = get_health_response()
        task_status_totals = Task.get_status_totals()
        return {
            "items": [
                {
                    "total_news_items": total_news_items,
                    "total_story_items": total_story_items,
                    "total_products": total_products,
                    "report_items_completed": report_items_completed,
                    "report_items_in_progress": report_items_in_progress,
                    "latest_collected": latest_collected,
                    "schedule_length": schedule_length,
                    "conflict_count": conflict_count,
                    "health_status": health_status,
                    "task_status_totals": task_status_totals,
                }
            ]
        }
