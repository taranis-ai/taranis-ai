from flask import request
from flask_jwt_extended import jwt_required
from flask_restful import Resource

from core.managers.log_manager import logger
from core.model.news_item import NewsItemData, NewsItemTag, NewsItemAggregate
from core.model.product import Product
from core.model.report_item import ReportItem
from core.model.tag_cloud import TagCloud


class Dashboard(Resource):
    @jwt_required()
    def get(self):
        total_news_items = NewsItemData.count_all()
        total_products = Product.count_all()
        report_items_completed = ReportItem.count_all(True)
        report_items_in_progress = ReportItem.count_all(False)
        total_database_items = total_news_items + total_products + report_items_completed + report_items_in_progress
        latest_collected = NewsItemData.latest_collected()
        return {
            "total_news_items": total_news_items,
            "total_products": total_products,
            "report_items_completed": report_items_completed,
            "report_items_in_progress": report_items_in_progress,
            "total_database_items": total_database_items,
            "latest_collected": latest_collected,
        }


class TrendingClusters(Resource):
    @jwt_required()
    def get(self):
        try:
            days = int(request.args.get("days", 7))
            limit = int(request.args.get("limit", 12))
            return NewsItemTag.find_largest_tag_clusters(days, limit)
        except Exception:
            logger.log_debug_trace()
            return "", 400


class StoryClusters(Resource):
    @jwt_required()
    def get(self):
        try:
            days = int(request.args.get("days", 7))
            limit = int(request.args.get("limit", 12))
            return NewsItemAggregate.get_story_clusters(days, limit)
        except Exception:
            logger.log_debug_trace()
            return "", 400


class Tagcloud(Resource):
    @jwt_required()
    def get(self):
        try:
            tag_cloud_day = 0
            if "tag_cloud_day" in request.args and request.args["tag_cloud_day"]:
                tag_cloud_day = min(int(request.args["tag_cloud_days"]), 7)
        except Exception as ex:
            logger.log_debug(ex)
            return "", 400

        return TagCloud.get_grouped_words(tag_cloud_day)


def initialize(api):
    api.add_resource(Dashboard, "/api/v1/dashboard-data")
    api.add_resource(Tagcloud, "/api/v1/tagcloud")
    api.add_resource(TrendingClusters, "/api/v1/trending-clusters")
    api.add_resource(StoryClusters, "/api/v1/story-clusters")
