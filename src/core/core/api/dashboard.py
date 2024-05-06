from flask import request, Flask
from flask.views import MethodView
from flask_jwt_extended import jwt_required

from core.model.news_item import NewsItem
from core.model.story import Story
from core.model.news_item_tag import NewsItemTag
from core.service.news_item_tag import NewsItemTagService
from core.model.product import Product
from core.model.report_item import ReportItem
from core.model.queue import ScheduleEntry
from core.config import Config


class Dashboard(MethodView):
    @jwt_required()
    def get(self):
        total_news_items = NewsItem.get_count()
        total_products = Product.get_count()
        report_items_completed = ReportItem.count_all(True)
        report_items_in_progress = ReportItem.count_all(False)
        total_database_items = total_news_items + total_products + report_items_completed + report_items_in_progress
        latest_collected = NewsItem.latest_collected()
        schedule_lenght = ScheduleEntry.get_count()
        return {
            "total_news_items": total_news_items,
            "total_products": total_products,
            "report_items_completed": report_items_completed,
            "report_items_in_progress": report_items_in_progress,
            "total_database_items": total_database_items,
            "latest_collected": latest_collected,
            "schedule_lenght": schedule_lenght,
        }, 200


class TrendingClusters(MethodView):
    @jwt_required()
    def get(self):
        return NewsItemTagService.get_largest_tag_types()


class StoryClusters(MethodView):
    @jwt_required()
    def get(self):
        days = int(request.args.get("days", 7))
        limit = int(request.args.get("limit", 12))
        return Story.get_story_clusters(days, limit)


class ClusterByType(MethodView):
    @jwt_required()
    def get(self, tag_type: str):
        per_page = min(int(request.args.get("per_page", 50)), 100)
        page = int(request.args.get("page", 0))
        sort = request.args.get("sort_by")
        offset = min(((page - 1) * per_page), (2**31) - 1)
        filter_args = {"tag_type": tag_type, "limit": per_page, "offset": offset, "sort": sort}
        return NewsItemTag.get_cluster_by_filter(filter_args)


class BuildInfo(MethodView):
    @jwt_required()
    def get(self):
        result = {"build_date": Config.BUILD_DATE.isoformat()}
        if Config.GIT_INFO:
            result |= Config.GIT_INFO
        return result


def initialize(app: Flask):
    base_route = "/api/dashboard"
    app.add_url_rule(f"{base_route}/", view_func=Dashboard.as_view("dashboard"))
    app.add_url_rule(f"{base_route}", view_func=Dashboard.as_view("dashboard_"))
    app.add_url_rule(f"{base_route}/trending-clusters", view_func=TrendingClusters.as_view("trending-clusters"))
    app.add_url_rule(f"{base_route}/story-clusters", view_func=StoryClusters.as_view("story-clusters"))
    app.add_url_rule(f"{base_route}/cluster/<string:tag_type>", view_func=ClusterByType.as_view("cluster-by-type"))
    app.add_url_rule(f"{base_route}/build-info", view_func=BuildInfo.as_view("build-info"))
