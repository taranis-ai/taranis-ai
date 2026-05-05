from models.admin import Worker

from frontend.views.admin_views.admin_mixin import AdminMixin
from frontend.views.base_view import BaseView


class WorkerView(AdminMixin, BaseView):
    model = Worker
    icon = "wallet"
    _index = 60
    _read_only = True

    edit_route = "admin.edit_worker_type"
