from models.admin import Job
from frontend.views.base_view import BaseView
from frontend.views.admin_mixin import AdminMixin


class SchedulerView(AdminMixin, BaseView):
    model = Job
    icon = "calendar-days"
    htmx_list_template = "schedule/index.html"
    htmx_update_template = "schedule/index.html"
    default_template = "schedule/index.html"
    base_route = "admin.scheduler"
    _read_only = True
    _index = 61

    def get(self, **kwargs) -> tuple[str, int]:
        return self.static_view()
