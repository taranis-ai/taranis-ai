from models.dashboard import Dashboard, TrendingCluster
from frontend.views.base_view import BaseView
from flask import render_template, abort

from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.auth import auth_required


class DashboardView(BaseView):
    model = Dashboard
    icon = "home"
    htmx_list_template = "dashboard/index.html"
    htmx_update_template = "dashboard/index.html"
    default_template = "dashboard/index.html"
    base_route = "base.dashboard"
    _read_only = True
    _index = 10

    @classmethod
    def static_view(cls):
        error = None
        try:
            dashboard = DataPersistenceLayer().get_objects(cls.model)
        except Exception as exc:
            dashboard = None
            error = str(exc)

        try:
            trending_clusters = DataPersistenceLayer().get_objects(TrendingCluster)
        except Exception:
            trending_clusters = []

        if error or not dashboard:
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("errors/404.html", error="No Dashboard items found")
        template = cls.get_list_template()
        context = {"data": dashboard[0], "clusters": trending_clusters, "error": error}
        logger.debug(f"Rendering {template} with context: {context}")
        return render_template(template, **context)

    @classmethod
    def admin_dashboard(cls):
        dashboard = DataPersistenceLayer().get_objects(cls.model)

        if not dashboard:
            logger.error(f"Error retrieving {cls.model_name()}")
            return render_template("errors/404.html", error="No Dashboard items found")

        return render_template("admin_dashboard/index.html", data=dashboard[0])

    @auth_required()
    def get(self, **kwargs):
        return self.static_view()

    @auth_required()
    def post(self):
        abort(405)

    @auth_required()
    def put(self, **kwargs):
        abort(405)

    @auth_required()
    def delete(self, **kwargs):
        abort(405)
