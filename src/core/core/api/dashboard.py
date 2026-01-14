from flask import Blueprint, Flask, jsonify, request
from flask.views import MethodView
from flask_jwt_extended import current_user

from core.config import Config
from core.log import logger
from core.managers.auth_manager import auth_required
from core.model.news_item_tag import NewsItemTag
from core.service.dashboard import DashboardService
from core.service.news_item_tag import NewsItemTagService
from core.service.story import StoryService


class Dashboard(MethodView):
    @auth_required()
    def get(self):
        return DashboardService.get_dashboard_data(), 200


class ClusterNames(MethodView):
    @auth_required()
    def get(self):
        return {"items": NewsItemTagService.get_tag_types()}, 200


class TrendingClusters(MethodView):
    @auth_required()
    def get(self):
        dashboard_settings = current_user.profile.get("dashboard", {})

        trending_cluster_days = dashboard_settings.get("trending_cluster_days", 7)
        trending_cluster_filter = dashboard_settings.get("trending_cluster_filter", None)
        logger.debug(f"{trending_cluster_days=}, {trending_cluster_filter=}")
        days = int(request.args.get("days", trending_cluster_days))
        legacy = request.args.get("legacy", "false").lower() == "true"
        if legacy:
            return NewsItemTagService.get_largest_tag_types(days)

        items = list(NewsItemTagService.get_largest_tag_types(days).values())

        if trending_cluster_filter:
            items = [tag for tag in items if tag.get("name") in trending_cluster_filter]

        return {"items": items}, 200


class StoryClusters(MethodView):
    @auth_required()
    def get(self):
        days = int(request.args.get("days", 7))
        limit = int(request.args.get("limit", 12))
        return jsonify(StoryService.get_story_clusters(days, limit))


class ClusterByType(MethodView):
    @auth_required()
    def get(self, tag_type: str):
        limit = min(request.args.get("limit", default=20, type=int), 100)
        page = request.args.get("page", default=1, type=int)
        sort = request.args.get("order", default="size_desc")
        offset = min((page - 1) * limit, (2**31) - 1)
        search = request.args.get("search")
        filter_args = {"tag_type": tag_type, "limit": limit, "offset": offset, "sort": sort, "search": search}
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
    dashboard_bp.add_url_rule("/cluster-names", view_func=ClusterNames.as_view("cluster-names"))
    dashboard_bp.add_url_rule("/story-clusters", view_func=StoryClusters.as_view("story-clusters"))
    dashboard_bp.add_url_rule("/cluster/<string:tag_type>", view_func=ClusterByType.as_view("cluster-by-type"))
    dashboard_bp.add_url_rule("/build-info", view_func=BuildInfo.as_view("build-info"))
    dashboard_bp.add_url_rule("/delete-tag/<string:tag_name>", view_func=DeleteTag.as_view("delete-tag"))

    app.register_blueprint(dashboard_bp)
