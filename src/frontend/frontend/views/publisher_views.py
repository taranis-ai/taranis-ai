from frontend.views.base_view import BaseView
from models.admin import PublisherPreset, ProductType

from frontend.filters import render_item_type


class PublisherView(BaseView):
    model = PublisherPreset
    icon = "envelope-open"
    _index = 140


class ProductTypeView(BaseView):
    model = ProductType
    icon = "envelope"
    _index = 150

    @classmethod
    def get_columns(cls):
        return [
            {"title": "ID", "field": "id", "sortable": False, "renderer": None},
            {"title": "Title", "field": "title", "sortable": True, "renderer": None},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
            {"title": "Type", "field": "type", "sortable": False, "renderer": render_item_type},
        ]
