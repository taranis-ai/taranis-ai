import worker.presenters
from worker.presenters.base_presenter import BasePresenter
from worker.log import logger
from worker.core_api import CoreApi
from requests.exceptions import ConnectionError

core_api = CoreApi()

presenters = {
    "html_presenter": worker.presenters.HTMLPresenter(),
    "json_presenter": worker.presenters.JSONPresenter(),
    "pdf_presenter": worker.presenters.PDFPresenter(),
    "text_presenter": worker.presenters.TextPresenter(),
}


def get_product(product_id: int) -> tuple[dict[str, str] | None, str | None]:
    try:
        product = core_api.get_product(product_id)
    except ConnectionError as e:
        logger.critical(e)
        return None, str(e)

    if not product:
        logger.error(f"Product with id {product_id} not found")
        return None, f"Product with id {product_id} not found"
    return product, None


def get_template(presenter: int) -> tuple[str | None, None | str]:
    try:
        template = core_api.get_template(presenter)
    except ConnectionError as e:
        logger.critical(e)
        return None, str(e)

    if not template:
        logger.error(f"presenter with id {presenter} not found")
        return None, f"presenter with id {presenter} not found"
    return template, None


def get_presenter(product) -> tuple[BasePresenter | None, str | None]:
    presenter_type = product.get("type")
    if not presenter_type:
        logger.error(f"Product {product['id']} has no presenter_type")
        return None, f"Product {product['id']} has no presenter_type"

    if presenter := presenters.get(presenter_type):
        return presenter, None

    return None, f"Presenter {presenter_type} not implemented"


def render_product(product_id: int):
    err = None

    product, err = get_product(product_id)
    if err or not product:
        return err

    presenter, err = get_presenter(product)
    if err or not presenter:
        return err

    type_id: int = int(product["type_id"])
    template, err = get_template(type_id)
    if err or not product:
        return err

    rendered_product = presenter.generate(product, template)
    if not rendered_product:
        return "Error generating product"
    if "error" in rendered_product:
        return rendered_product["error"]

    core_api.upload_rendered_product(
        product_id,
        rendered_product,
    )
    return "Product rendered successfully"
