from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Resource, Namespace, Api

from core.managers.log_manager import logger
from core.model.news_item import NewsItemData, NewsItemTag, NewsItemAggregate
from core.model.product import Product
from core.model.report_item import ReportItem
from core.config import Config


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
            return NewsItemTag.get_largest_tag_types()
            # return NewsItemTag.find_largest_tag_clusters(days, limit)
        except Exception as e:
            logger.log_debug_trace()
            return {"error": str(e)}, 400


class StoryClusters(Resource):
    @jwt_required()
    def get(self):
        try:
            days = int(request.args.get("days", 7))
            limit = int(request.args.get("limit", 12))
            return NewsItemAggregate.get_story_clusters(days, limit)
        except Exception as e:
            logger.log_debug_trace()
            return {"error": str(e)}, 400


class ClusterByType(Resource):
    @jwt_required()
    def get(self, tag_type: str):
        try:
            per_page = min(int(request.args.get("per_page", 50)), 100)
            page = int(request.args.get("page", 0))
            offset = min(((page - 1) * per_page), (2**31) - 1)
            filter_args = {"tag_type": tag_type, "limit": per_page, "offset": offset}
            return NewsItemTag.get_cluster_by_filter(filter_args)
        except Exception as e:
            logger.log_debug_trace()
            return {"error": str(e)}, 400


class Tagcloud(Resource):
    @jwt_required()
    def get(self):
        # TODO: should be just a list of tags and their counts
        return {"message": "Not implemented"}, 501


class BuildInfo(Resource):
    @jwt_required()
    def get(self):
        result = {"build_date": Config.BUILD_DATE.isoformat()}
        if Config.GIT_INFO:
            result |= Config.GIT_INFO
        return result


def initialize(api: Api):
    namespace = Namespace("dashboard", description="Dashboard related operations")
    namespace.add_resource(Dashboard, "/", "")
    namespace.add_resource(Tagcloud, "/tagcloud")
    namespace.add_resource(TrendingClusters, "/trending-clusters")
    namespace.add_resource(StoryClusters, "/story-clusters")
    namespace.add_resource(ClusterByType, "/cluster/<string:tag_type>")
    namespace.add_resource(BuildInfo, "/build-info")
    api.add_namespace(namespace, path="/dashboard")
