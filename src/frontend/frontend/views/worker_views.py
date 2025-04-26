# role_views.py
from frontend.models import Worker
from frontend.views.base_view import BaseView


class WorkerView(BaseView):
    model = Worker
