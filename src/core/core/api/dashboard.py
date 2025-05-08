from flask import Blueprint, request, Flask
from flask.views import MethodView

from core.model.news_item import NewsItem
from core.model.news_item_tag import NewsItemTag
from core.service.news_item_tag import NewsItemTagService
from core.service.story import StoryService
from core.model.product import Product
from core.model.report_item import ReportItem
from core.managers.auth_manager import auth_required
from core.managers import schedule_manager
from core.config import Config
from core.model.story_conflict import StoryConflict


class Dashboard(MethodView):
    @auth_required()
    def get(self):
        total_news_items = NewsItem.get_count()
        total_products = Product.get_count()
        report_items_completed = ReportItem.count_all(True)
        report_items_in_progress = ReportItem.count_all(False)
        total_database_items = total_news_items + total_products + report_items_completed + report_items_in_progress
        latest_collected = NewsItem.latest_collected()
        schedule_length = len(schedule_manager.schedule.get_periodic_tasks())
        return {
            "items": [
                {
                    "total_news_items": total_news_items,
                    "total_products": total_products,
                    "report_items_completed": report_items_completed,
                    "report_items_in_progress": report_items_in_progress,
                    "total_database_items": total_database_items,
                    "latest_collected": latest_collected,
                    "schedule_length": schedule_length,
                    "conflict_count": len(StoryConflict.conflict_store),
                }
            ]
        }, 200


class TrendingClusters(MethodView):
    @auth_required()
    def get(self):
        days = int(request.args.get("days", 7))
        return NewsItemTagService.get_largest_tag_types(days)


class StoryClusters(MethodView):
    @auth_required()
    def get(self):
        days = int(request.args.get("days", 7))
        limit = int(request.args.get("limit", 12))
        return StoryService.get_story_clusters(days, limit)


class ClusterByType(MethodView):
    @auth_required()
    def get(self, tag_type: str):
        per_page = min(int(request.args.get("per_page", 50)), 100)
        page = int(request.args.get("page", 0))
        sort = request.args.get("sort_by")
        offset = min(((page - 1) * per_page), (2**31) - 1)
        search = request.args.get("search", None)
        filter_args = {"tag_type": tag_type, "limit": per_page, "offset": offset, "sort": sort, "search": search}
        return NewsItemTag.get_cluster_by_filter(filter_args)


class DeleteTag(MethodView):
    @auth_required()
    def delete(self, tag_name: str):
        NewsItemTagService.delete_tags_by_name(tag_name)
        return {"message": f"Cluster {tag_name} deleted"}, 200


class BuildInfo(MethodView):
    @auth_required()
    def get(self):
        result = {"build_date": Config.BUILD_DATE.isoformat()}
        if Config.GIT_INFO:
            result |= Config.GIT_INFO
        return result


def initialize(app: Flask):
    dashboard_bp = Blueprint("dashboard", __name__, url_prefix=f"{Config.APPLICATION_ROOT}api/dashboard")

    dashboard_bp.add_url_rule("", view_func=Dashboard.as_view("dashboard"))
    dashboard_bp.add_url_rule("/trending-clusters", view_func=TrendingClusters.as_view("trending-clusters"))
    dashboard_bp.add_url_rule("/story-clusters", view_func=StoryClusters.as_view("story-clusters"))
    dashboard_bp.add_url_rule("/cluster/<string:tag_type>", view_func=ClusterByType.as_view("cluster-by-type"))
    dashboard_bp.add_url_rule("/build-info", view_func=BuildInfo.as_view("build-info"))
    dashboard_bp.add_url_rule("/delete-tag/<string:tag_name>", view_func=DeleteTag.as_view("delete-tag"))

    app.register_blueprint(dashboard_bp)
