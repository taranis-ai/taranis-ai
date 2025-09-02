from models.product import Product
from frontend.views.base_view import BaseView


class PublishView(BaseView):
    model = Product
    icon = "paper-airplane"
    htmx_list_template = "publish/index.html"
    htmx_update_template = "publish/index.html"
    default_template = "publish/index.html"

    base_route = "publish.publish"
    edit_route = "publish.publish"
    _read_only = False
