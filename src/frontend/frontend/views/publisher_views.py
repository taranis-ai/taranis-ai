from frontend.views.base_view import BaseView
from models.admin import PublisherPreset, ProductType


class PublisherView(BaseView):
    model = PublisherPreset


class ProductTypeView(BaseView):
    model = ProductType
