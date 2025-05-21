from frontend.views.base_view import BaseView
from models.admin import Connector


class ConnectorView(BaseView):
    model = Connector
    icon = "link"
    _index = 115
