from flask import render_template, abort


from models.dashboard import Dashboard
from frontend.views.admin_views.admin_mixin import AdminMixin
from frontend.views.base_view import BaseView
from frontend.data_persistence import DataPersistenceLayer
from frontend.log import logger
from frontend.config import Config


class AdminDashboardView(AdminMixin, BaseView):
    model = Dashboard
    icon = "home"
    htmx_list_template = "admin_dashboard/index.html"
    htmx_update_template = "admin_dashboard/index.html"
    default_template = "admin_dashboard/index.html"
    base_route = "admin.dashboard"
    _read_only = True
    _index = 10

    @classmethod
    def pretty_name(cls) -> str:
        return "Admin Dashboard"

    @classmethod
    def static_view(cls):
        error = None
        try:
            dashboard = DataPersistenceLayer().get_objects(cls.model)
        except Exception as exc:
            dashboard = None
            error = str(exc)

        if error or not dashboard:
            logger.error(f"Error retrieving {cls.model_name()} items: {error}")
            return render_template("errors/404.html", error="No Dashboard items found"), 404
        template = cls.get_list_template()
        context = {"data": dashboard[0], "build_info": cls.get_build_info(), **cls._common_context(error)}
        return render_template(template, **context), 200

    @classmethod
    def get_build_info(cls):
        result = {"build_date": Config.BUILD_DATE.isoformat()}
        if Config.GIT_INFO:
            result |= Config.GIT_INFO
        return result

    def get(self, **kwargs):
        return self.static_view()

    def post(self):
        return abort(405)

    def put(self, **kwargs):
        return abort(405)

    def delete(self, **kwargs):
        return abort(405)
