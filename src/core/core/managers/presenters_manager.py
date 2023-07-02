from core.model.presenters_node import PresentersNode
from core.model.presenter import Presenter
from core.model.product import Product
from core.remote.presenters_api import PresentersApi
from core.managers.log_manager import logger


def get_presenters_info(node: PresentersNode):
    try:
        presenters_info, status_code = PresentersApi(node.api_url, node.api_key).get_presenters_info()
    except ConnectionError:
        return f"Connection error: Could not reach {node.api_url}", 500
    except Exception:
        logger.log_debug_trace(f"Couldn't add Presenter Node: {node.name}")
        return f"Couldn't add Presenter node: {node.name}", 500

    if status_code != 200:
        return None, status_code

    return Presenter.load_multiple(presenters_info), status_code


def update_presenters_node(node_id, data):
    node = PresentersNode.get(node_id)
    if not node:
        return
    presenters, status_code = get_presenters_info(node)

    if status_code != 200:
        return presenters, status_code

    try:
        PresentersNode.update(node_id, data, presenters)
    except Exception:
        logger.log_debug_trace(f"Couldn't add Presenter Node: {node.name}")
        return f"Couldn't add Presenter node: {node.name}", 500

    return node.id, status_code


def generate_product(product_id):
    product = Product.get(product_id)
    if not product:
        return
    presenter = product.product_type.presenter
    node = presenter.node

    input_data = {
        "type": presenter.type,
        "parameter_values": product.product_type.parameter_values,
        "report_items": product.report_items,
        "report_type": product.report_items[0].report_item_type,
    }

    return PresentersApi(node.api_url, node.api_key).generate(input_data)
