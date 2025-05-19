from frontend.views.base_view import BaseView
from models.admin import PublisherPreset, ProductType


class PublisherView(BaseView):
    model = PublisherPreset
    icon = "envelope-open"
    _index = 140


class ProductTypeView(BaseView):
    model = ProductType
    icon = "envelope"
    _index = 150
