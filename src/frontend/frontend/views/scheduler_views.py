from models.admin import Job
from frontend.views.base_view import BaseView


class SchedulerView(BaseView):
    model = Job
    icon = "calendar-days"
    htmx_list_template = "schedule/index.html"
    htmx_update_template = "schedule/index.html"
    default_template = "schedule/index.html"
    base_route = "admin.scheduler"
    _index = 10
