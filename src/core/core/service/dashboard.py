from datetime import timedelta

from core.managers import queue_manager
from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.news_item import NewsItem
from core.model.news_item_conflict import NewsItemConflict
from core.model.product import Product
from core.model.report_item import ReportItem
from core.model.story import Story
from core.model.story_conflict import StoryConflict
from core.model.task import Task
from core.service.health import get_health_response


class DashboardService:
    @classmethod
    def get_dashboard_data(cls) -> dict:
        now = BaseModel.utcnow()
        week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        news_items_this_week = NewsItem.get_filtered_count(db.select(NewsItem.id).where(NewsItem.published.between(week_start, now)))
        stories_this_week = Story.get_filtered_count(db.select(Story.id).where(Story.created.between(week_start, now)))
        reports_this_week = ReportItem.get_filtered_count(db.select(ReportItem.id).where(ReportItem.created.between(week_start, now)))
        products_this_week = Product.get_filtered_count(db.select(Product.id).where(Product.created.between(week_start, now)))
        total_news_items = NewsItem.get_count()
        total_story_items = Story.get_count()
        total_products = Product.get_count()
        report_items_completed = ReportItem.count_all(True)
        report_items_in_progress = ReportItem.count_all(False)
        latest_collected = NewsItem.latest_collected()
        schedule_length = queue_manager.queue_manager.get_scheduled_job_count()
        conflict_count = len(StoryConflict.conflict_store) + len(NewsItemConflict.conflict_store)
        health_status, _ = get_health_response()
        task_status_totals = Task.get_status_totals()
        return {
            "items": [
                {
                    "news_items_this_week": news_items_this_week,
                    "stories_this_week": stories_this_week,
                    "reports_this_week": reports_this_week,
                    "products_this_week": products_this_week,
                    "story_conflict_count": len(StoryConflict.conflict_store),
                    "news_item_conflict_count": len(NewsItemConflict.conflict_store),
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
