from frontend.views.base_view import BaseView
from models.admin import Connector


class ConnectorView(BaseView):
    model = Connector
    icon = "link"
    _index = 115

    _read_only = True  # TODO: Remove this when we implement create/update/delete for Connectors
