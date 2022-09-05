from core.model.presenters_node import PresentersNode
from core.model.presenter import Presenter
from core.model.product import Product
from core.remote.presenters_api import PresentersApi
from core.managers.log_manager import logger
from shared.schema.presenters_node import PresentersNode as PresentersNodeSchema
from shared.schema.presenter import PresenterInput, PresenterInputSchema


def get_presenters_info(node: PresentersNodeSchema):
    try:
        presenters_info, status_code = PresentersApi(node.api_url, node.api_key).get_presenters_info()
    except ConnectionError:
        return f"Connection error: Could not reach {node.api_url}", 500
    except Exception:
        logger.log_debug_trace(f"Couldn't add Presenter Node: {node.name}")
        return f"Couldn't add Presenter node: {node.name}", 500

    if status_code != 200:
        return None, status_code

    return Presenter.create_all(presenters_info), status_code


def add_presenters_node(data):
    try:
        logger.log_info(data)
        presenters_info = data.pop("presenters_info")
        node = PresentersNodeSchema.create(data)
    except Exception as e:
        logger.log_debug_trace()
        return str(e), 500

    try:
        presenters = Presenter.create_all(presenters_info)
        PresentersNode.add_new(data, presenters)
    except Exception:
        logger.log_debug_trace(f"Couldn't add Presenter Node: {node.name}")
        return f"Couldn't add Presenter Node: {node.name}", 500

    return node.id, 200


def update_presenters_node(node_id, data):
    node = PresentersNodeSchema.create(data)
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
    product = Product.find(product_id)
    presenter = product.product_type.presenter
    node = presenter.node

    input_data = PresenterInput(
        presenter.type,
        product.product_type.parameter_values,
        product.report_items,
        product.report_items[0].report_item_type,
    )
    input_schema = PresenterInputSchema()

    return PresentersApi(node.api_url, node.api_key).generate(input_schema.dump(input_data))
