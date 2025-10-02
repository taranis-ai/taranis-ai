from models.admin import Worker
from frontend.views.base_view import BaseView
from frontend.views.admin_views.admin_mixin import AdminMixin


class WorkerView(AdminMixin, BaseView):
    model = Worker
    icon = "wallet"
    _index = 60
    _read_only = True
