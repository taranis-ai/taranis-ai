from frontend.views.base_view import BaseView
from models.admin import Attribute


class AttributeView(BaseView):
    model = Attribute
    icon = "document-arrow-up"
    _index = 130
