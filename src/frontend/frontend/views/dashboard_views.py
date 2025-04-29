from models.admin import Dashboard, TrendingClusters
from frontend.views.base_view import BaseView
from flask import render_template

from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger


class DashboardView(BaseView):
    model = Dashboard
    htmx_list_template = "dashboard/index.html"
    htmx_update_template = "dashboard/index.html"
    default_template = "dashboard/index.html"
    base_route = "base.dashboard"

    @classmethod
    def static_view(cls):
        try:
            dashboard = DataPersistenceLayer().get_objects(cls.model)
            trending_clusters = DataPersistenceLayer().get_objects(TrendingClusters)
            error = None
        except Exception as exc:
            dashboard = None
            trending_clusters = None
            error = str(exc)

        if not dashboard or not trending_clusters:
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("errors/404.html", error="No Dashboard items found")
        template = cls.get_list_template()
        return render_template(template, **{"dashboard": dashboard, "cluster": trending_clusters, "error": error})
