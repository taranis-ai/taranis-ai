from models.admin import Worker
from frontend.views.base_view import BaseView


class WorkerView(BaseView):
    model = Worker
    icon = "wallet"
    _index = 60
