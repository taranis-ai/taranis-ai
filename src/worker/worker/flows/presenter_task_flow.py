from prefect import flow, task
from base64 import b64encode
from requests.exceptions import ConnectionError
from worker.log import logger
from models.prefect import PresenterTaskRequest
from worker.core_api import CoreApi
import worker.presenters


@task
def get_product_info(product_id: int):
    """Get product information from CoreApi"""
    logger.info(f"[presenter_task] Getting product info for {product_id}")

    core_api = CoreApi()
    product = None

    try:
        product = core_api.get_product(product_id)
    except ConnectionError as e:
        raise ValueError(f"Unable to connect to core API: {e}") from e

    if not product:
        raise ValueError(f"Product with id {product_id} not found")

    return product


@task
def get_template_info(type_id: int):
    """Get template information from CoreApi"""
    logger.info(f"[presenter_task] Getting template info for type_id {type_id}")

    core_api = CoreApi()

    try:
        template = core_api.get_template(type_id)
    except ConnectionError as e:
        raise ValueError(f"Unable to connect to core API: {e}") from e

    if not template:
        raise ValueError(f"Template with id {type_id} not found")

    return template


@task
def get_presenter_instance(product: dict):
    """Get presenter instance from registry"""
    logger.info("[presenter_task] Getting presenter instance for product")

    presenters = {
        "html_presenter": worker.presenters.HTMLPresenter(),
        "json_presenter": worker.presenters.JSONPresenter(),
        "pdf_presenter": worker.presenters.PDFPresenter(),
        "text_presenter": worker.presenters.TextPresenter(),
    }

    presenter_type = product.get("type")
    if not presenter_type:
        raise ValueError(f"Product {product['id']} has no presenter_type")

    presenter = presenters.get(presenter_type)
    if not presenter:
        raise ValueError(f"Presenter {presenter_type} not implemented")

    return presenter


@task
def generate_product_content(presenter, product: dict, template: str, product_id: int):
    """Generate product content"""
    logger.info(f"[presenter_task] Generating content for product {product_id}")

    logger.info(f"Rendering product {product_id} with presenter {presenter.type}")

    # Generate content
    rendered_product = presenter.generate(product, template)

    if not rendered_product:
        raise ValueError(f"Presenter {presenter.type} returned no content")

    # Encode to base64
    if isinstance(rendered_product, str):
        encoded_product = b64encode(rendered_product.encode("utf-8")).decode("ascii")
    else:
        encoded_product = b64encode(rendered_product).decode("ascii")

    return encoded_product


@flow(name="presenter-task-flow")
def presenter_task_flow(request: PresenterTaskRequest):
    try:
        logger.info("[presenter_task_flow] Starting presenter task ")

        # Convert string product_id to int
        product_id = int(request.product_id)

        # Get product info
        product = get_product_info(product_id)

        # Get presenter instance
        presenter = get_presenter_instance(product)

        # Get template
        type_id = int(product["type_id"])
        template = get_template_info(type_id)

        # Generate and encode content
        encoded_product = generate_product_content(presenter, product, template, product_id)

        logger.info("[presenter_task_flow] Presenter task completed successfully")

        return {"product_id": product_id, "message": f"Product: {product_id} rendered successfully", "render_result": encoded_product}

    except Exception:
        logger.exception("[presenter_task_flow] Presenter task failed")
        raise
