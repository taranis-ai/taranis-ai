from core.model.product import Product
from core.remote.presenters_api import PresentersApi
from core.managers.log_manager import logger


def generate_product(product_id):
    product = Product.get(product_id)
    if not product:
        return
    presenter = product.product_type.presenter
    node = presenter.node

    input_data = {
        "type": presenter.type,
        "parameters": product.product_type.parameters,
        "report_items": product.report_items,
        "report_type": product.report_items[0].report_item_type,
    }

    return PresentersApi(node.api_url, node.api_key).generate(input_data)
