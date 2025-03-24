from prefect import flow, get_run_logger
import worker.presenters
from worker.presenters.base_presenter import BasePresenter
from worker.core_api import CoreApi


def get_product(product_id: int, core_api: CoreApi) -> dict[str, str]:
    if product := core_api.get_product(product_id):
        return product

    raise ValueError(f"Product with id {product_id} not found")


def get_template(presenter_id: int, core_api: CoreApi) -> str:
    if template := core_api.get_template(presenter_id):
        return template

    raise ValueError(f"Template with id {presenter_id} not found")


def get_presenter(product: dict[str, str]) -> BasePresenter:
    presenters: dict[str, BasePresenter] = {
        "html_presenter": worker.presenters.HTMLPresenter(),
        "json_presenter": worker.presenters.JSONPresenter(),
        "pdf_presenter": worker.presenters.PDFPresenter(),
        "text_presenter": worker.presenters.TextPresenter(),
    }

    presenter_type = product.get("type")
    if not presenter_type:
        raise ValueError(f"Product {product['id']} has no presenter_type")

    if presenter := presenters.get(presenter_type):
        return presenter

    raise ValueError(f"Presenter {presenter_type} not implemented")


def generate_content(product: dict[str, str], template: str, presenter: BasePresenter) -> dict[str, str | bytes]:
    if rendered_content := presenter.generate(product, template):
        return rendered_content
    raise ValueError("Presenter returned no content")


@flow(name="render_product")
def render_product(product_id: int):
    logger = get_run_logger()
    core_api = CoreApi()

    try:
        product = get_product(product_id, core_api)
        presenter = get_presenter(product)
        type_id = int(product["type_id"])
        template = get_template(type_id, core_api)

        logger.info(f"Rendering product {product_id} with presenter {presenter.type}")

        rendered_product = generate_content(product, template, presenter)

        logger.info(f"Product {product_id} rendered successfully")

        return {
            "product_id": product_id,
            "message": f"Product: {product_id} rendered successfully",
            "render_result": rendered_product,
        }

    except Exception as e:
        logger.error(f"Error rendering product {product_id}: {e}")
        raise
