from models.admin import Worker

from frontend.views.admin_views.admin_base_view import AdminBaseView


class WorkerView(AdminBaseView):
    model = Worker
    icon = "wallet"
    _index = 60
    _read_only = True

    edit_route = "admin.edit_worker_type"
