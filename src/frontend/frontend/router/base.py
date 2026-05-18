from urllib.parse import urlencode

from flask import Blueprint, Flask, Response, jsonify, redirect, render_template, request, send_from_directory, url_for
from flask.views import MethodView

from frontend.assess_omnisearch import build_assess_omnisearch_suggestions, translate_assess_omnisearch
from frontend.auth import auth_required, logout
from frontend.cache import get_cache_keys, get_cached_users
from frontend.data_persistence import DataPersistenceLayer
from frontend.views import AuthView, DashboardView
from frontend.views.story_views import StoryView


class InvalidateCache(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self, suffix: str | None = None):
        response = DataPersistenceLayer().invalidate_cache(suffix)
        return ("Cache invalidated", response.status_code) if response.ok else (response.text, response.status_code)

    @auth_required("ADMIN_OPERATIONS")
    def post(self, suffix: str | None = None):
        response = DataPersistenceLayer().invalidate_cache(suffix)
        if not response.ok:
            return Response(response.text, status=response.status_code)
        return Response(status=204, headers={"HX-Refresh": "true"})


class ListCacheKeys(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self):
        return Response("<br>".join(get_cache_keys()))


class ListUserCache(MethodView):
    @auth_required("ADMIN_OPERATIONS")
    def get(self):
        return jsonify(get_cached_users())


class LogoutView(MethodView):
    def get(self):
        return logout()

    def delete(self):
        return logout()


class OpenAPIView(MethodView):
    @auth_required()
    def get(self):
        return render_template("open_api/index.html")


class NotificationView(MethodView):
    @auth_required()
    def get(self):
        return render_template("notification/index.html")


class HealthView(MethodView):
    def get(self):
        return render_template("health/index.html")


class FaviconView(MethodView):
    def get(self):
        return send_from_directory("static/assets", "favicon.ico", mimetype="image/vnd.microsoft.icon")


class OmniSearch(MethodView):
    @auth_required(["ASSESS_ACCESS", "ALL"])
    def get(self):
        current_search = request.args.get("q", "").strip()
        if "q" in request.args:
            if not current_search:
                return redirect(url_for("assess.assess"))

            filter_lists = StoryView._get_filter_lists()
            translation = translate_assess_omnisearch(current_search, filter_lists)
            if translation.errors:
                return (
                    render_template(
                        "partials/omnisearch/search_dialog.html",
                        current_search=current_search,
                        suggestions=build_assess_omnisearch_suggestions(current_search, filter_lists),
                        errors=translation.errors,
                    ),
                    400,
                )

            query_string = urlencode(translation.params, doseq=True)
            assess_url = url_for("assess.assess")
            return redirect(f"{assess_url}?{query_string}" if query_string else assess_url)

        return render_template("partials/omnisearch/search_dialog.html", current_search="")


class OmniSearchSuggestions(MethodView):
    @auth_required(["ASSESS_ACCESS", "ALL"])
    def get(self):
        current_search = request.args.get("q", "")
        filter_lists = StoryView._get_filter_lists()
        return render_template(
            "partials/omnisearch/suggestions.html",
            suggestions=build_assess_omnisearch_suggestions(current_search, filter_lists),
        )


class NewsItemConflictsView(MethodView):
    @auth_required("ASSESS_ACCESS")
    def get(self):
        return DashboardView.news_item_conflict_view()

    @auth_required("ASSESS_UPDATE")
    def post(self):
        return DashboardView.resolve_news_item_conflict_post()

    @auth_required("ASSESS_UPDATE")
    def put(self):
        return DashboardView.resolve_news_item_conflict_put()


def init(app: Flask):
    base_bp = Blueprint("base", __name__, url_prefix=app.config["APPLICATION_ROOT"])

    base_bp.add_url_rule("/health", view_func=HealthView.as_view("health"))
    base_bp.add_url_rule("/", view_func=DashboardView.as_view("dashboard"))
    base_bp.add_url_rule("/favicon.ico", view_func=FaviconView.as_view("favicon"))
    app.add_url_rule("/favicon.ico", view_func=FaviconView.as_view("favicon_base"))

    base_bp.add_url_rule("/dashboard", view_func=DashboardView.as_view("dashboard_"))
    base_bp.add_url_rule("/conflicts/menu", view_func=DashboardView.conflict_menu, methods=["GET"], endpoint="conflict_menu")
    base_bp.add_url_rule("/conflicts/stories", view_func=DashboardView.story_conflict_view, methods=["GET"], endpoint="story_conflicts")
    base_bp.add_url_rule(
        "/conflicts/story/<string:story_id>/resolve",
        view_func=DashboardView.resolve_story_conflict,
        methods=["POST"],
        endpoint="story_conflict_resolve",
    )
    base_bp.add_url_rule("/conflicts/news-items", view_func=NewsItemConflictsView.as_view("news_item_conflicts"))

    base_bp.add_url_rule("/cluster/<string:cluster_name>", view_func=DashboardView.get_cluster, methods=["GET"], endpoint="cluster")
    base_bp.add_url_rule("/dashboard/edit", view_func=DashboardView.edit_dashboard, methods=["GET"], endpoint="edit_dashboard_view")

    base_bp.add_url_rule("/login", view_func=AuthView.as_view("login"))
    base_bp.add_url_rule("/logout", view_func=LogoutView.as_view("logout"))
    base_bp.add_url_rule("/open_api", view_func=OpenAPIView.as_view("open_api"))
    base_bp.add_url_rule("/notification", view_func=NotificationView.as_view("notification"))
    base_bp.add_url_rule("/search", view_func=OmniSearch.as_view("omnisearch"))
    base_bp.add_url_rule("/search/suggestions", view_func=OmniSearchSuggestions.as_view("omnisearch_suggestions"))

    base_bp.add_url_rule("/invalidate_cache", view_func=InvalidateCache.as_view("invalidate_cache"))
    base_bp.add_url_rule("/invalidate_cache/<string:suffix>", view_func=InvalidateCache.as_view("invalidate_cache_suffix"))
    base_bp.add_url_rule("/list_cache_keys", view_func=ListCacheKeys.as_view("list_cache_keys"))
    base_bp.add_url_rule("/list_user_cache", view_func=ListUserCache.as_view("list_user_cache"))

    app.register_blueprint(base_bp)
