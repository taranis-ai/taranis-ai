from core.model.story import Story
from core.model.report_item import ReportItem
from core.model.product import Product
from core.model.news_item import NewsItem
from core.managers import schedule_manager
from core.model.story_conflict import StoryConflict
from core.model.task import Task


class DashboardService:
    @classmethod
    def get_dashboard_data(cls) -> dict:
        total_news_items = NewsItem.get_count()
        total_story_items = Story.get_count()
        total_products = Product.get_count()
        report_items_completed = ReportItem.count_all(True)
        report_items_in_progress = ReportItem.count_all(False)
        latest_collected = NewsItem.latest_collected()
        schedule_length = schedule_manager.schedule.get_periodic_tasks().get("total_count", 0)
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
                    "conflict_count": len(StoryConflict.conflict_store),
                    "worker_status": cls.get_worker_status(),
                }
            ]
        }

    @classmethod
    def get_worker_status(cls):
        return Task.get_status_counts_by_task()
