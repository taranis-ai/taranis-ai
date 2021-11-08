from model.presenters_node import PresentersNode
from model.presenter import Presenter
from model.product import Product
from remote.presenters_api import PresentersApi
from schema.presenters_node import PresentersNode as PresentersNodeSchema
from schema.presenter import PresenterInput, PresenterInputSchema


def add_presenters_node(data):
    node = PresentersNodeSchema.create(data)
    presenters_info, status_code = PresentersApi(node.api_url, node.api_key).get_presenters_info()
    if status_code == 200:
        presenters = Presenter.create_all(presenters_info)
        PresentersNode.add_new(data, presenters)

    return status_code


def update_presenters_node(node_id, data):
    node = PresentersNodeSchema.create(data)
    presenters_info, status_code = PresentersApi(node.api_url, node.api_key).get_presenters_info()
    if status_code == 200:
        presenters = Presenter.create_all(presenters_info)
        PresentersNode.update(node_id, data, presenters)

    return status_code


def generate_product(product_id):
    product = Product.find(product_id)
    presenter = product.product_type.presenter
    node = presenter.node

    input_data = PresenterInput(presenter.type, product.product_type.parameter_values, product.report_items,
                                product.report_items[0].report_item_type)
    input_schema = PresenterInputSchema()

    return PresentersApi(node.api_url, node.api_key).generate(input_schema.dump(input_data))
