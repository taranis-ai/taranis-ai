from models.admin import Dashboard
from frontend.views.base_view import BaseView
from flask import render_template, abort

from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.auth import auth_required


class DashboardView(BaseView):
    model = Dashboard
    icon = "home"
    htmx_list_template = "admin_dashboard/index.html"
    htmx_update_template = "admin_dashboard/index.html"
    default_template = "admin_dashboard/index.html"
    base_route = "admin.dashboard"
    _index = 10

    @classmethod
    def static_view(cls):
        try:
            dashboard = DataPersistenceLayer().get_objects(cls.model)
            trending_clusters = {}
            # trending_clusters = DataPersistenceLayer().get_objects(TrendingClusters)
            error = None
        except Exception as exc:
            dashboard = None
            trending_clusters = None
            error = str(exc)

        if not dashboard:
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("errors/404.html", error="No Dashboard items found")
        template = cls.get_list_template()
        return render_template(template, **{"data": dashboard[0], "cluster": trending_clusters, "error": error})

    @auth_required()
    def get(self, **kwargs):
        return self.static_view()

    @auth_required()
    def post(self):
        abort(501)

    @auth_required()
    def put(self, **kwargs):
        abort(501)

    @auth_required()
    def delete(self, **kwargs):
        abort(501)
