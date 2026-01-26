"""RQ Presenter Tasks

Functions for generating products/reports in various formats.
"""

from base64 import b64encode
from typing import Any

from requests.exceptions import ConnectionError
from rq import get_current_job

import worker.presenters
from worker.core_api import CoreApi
from worker.log import logger
from worker.presenters.base_presenter import BasePresenter


def presenter_task(product_id: str):
    """Generate a product/report in the specified format.

    Args:
        product_id: ID of the product to render

    Returns:
        dict: Result containing product_id, message, and base64-encoded rendered content

    Raises:
        ValueError: If product not found, misconfigured, or rendering fails
        ConnectionError: If unable to connect to core API
    """
    job = get_current_job()
    core_api = CoreApi()

    logger.info(f"Starting presenter task with job id {job.id if job else 'manual'}")

    # Get product configuration
    product = _get_product(core_api, product_id)

    # Get presenter for product type
    presenter = _get_presenter(product)

    # Get template if needed
    type_id: int = int(product["type_id"])
    if "TEMPLATE_PATH" in product.get("parameters", {}):
        template = _get_template(core_api, type_id)
    else:
        template = None

    logger.info(f"Rendering product {product_id} with presenter {presenter.type}")

    # Generate the product
    result_data = None
    if rendered_product := presenter.generate(product, template, parameters=product.get("parameters", {})):
        if isinstance(rendered_product, str):
            rendered_product = b64encode(rendered_product.encode("utf-8")).decode("ascii")
        else:
            rendered_product = b64encode(rendered_product).decode("ascii")

        result_data = {"product_id": product_id, "message": f"Product: {product_id} rendered successfully", "render_result": rendered_product}

        # Save task result to database
        if job:
            _save_task_result(job.id, "presenter_task", result_data, "SUCCESS", core_api)

        return result_data

    # Failed to generate product
    if job:
        error_msg = f"Presenter {presenter.type} returned no content"
        _save_task_result(job.id, "presenter_task", error_msg, "FAILURE", core_api)

    raise ValueError(f"Presenter {presenter.type} returned no content")


def _get_product(core_api: CoreApi, product_id: str) -> dict[str, Any]:
    """Fetch product configuration from core API.

    Args:
        core_api: CoreApi instance
        product_id: ID of the product

    Returns:
        Product configuration dictionary

    Raises:
        ValueError: If product not found
        ConnectionError: If unable to connect to core API
    """
    try:
        product = core_api.get_product(product_id)
    except ConnectionError as e:
        raise ValueError(f"Unable to connect to core API: {e}") from e

    if not product:
        raise ValueError(f"Product with id {product_id} not found")

    return product


def _get_template(core_api: CoreApi, presenter_id: int) -> str:
    """Fetch template from core API.

    Args:
        core_api: CoreApi instance
        presenter_id: ID of the presenter/template

    Returns:
        Template content

    Raises:
        ValueError: If template not found
        ConnectionError: If unable to connect to core API
    """
    try:
        template = core_api.get_template(presenter_id)
    except ConnectionError as e:
        raise ValueError(f"Unable to connect to core API: {e}") from e

    if not template:
        raise ValueError(f"Template with id {presenter_id} not found")

    return template


def _get_presenter(product: dict[str, Any]) -> BasePresenter:
    """Get the appropriate presenter for a product type.

    Args:
        product: Product configuration dictionary

    Returns:
        Presenter instance

    Raises:
        ValueError: If presenter type not found or not implemented
    """
    presenters = {
        "html_presenter": worker.presenters.HTMLPresenter(),
        "json_presenter": worker.presenters.JSONPresenter(),
        "pandoc_presenter": worker.presenters.PANDOCPresenter(),
        "pdf_presenter": worker.presenters.PDFPresenter(),
        "text_presenter": worker.presenters.TextPresenter(),
        "stix_presenter": worker.presenters.STIXPresenter(),
    }

    presenter_type = product.get("type")
    if not presenter_type:
        raise ValueError(f"Product {product['id']} has no presenter_type")

    if presenter := presenters.get(presenter_type):
        return presenter

    raise ValueError(f"Presenter {presenter_type} not implemented")


def _save_task_result(job_id: str, task_name: str, result: str | dict, status: str, core_api: CoreApi):
    """Save task execution result to Core API.

    Args:
        job_id: RQ job ID
        task_name: Name of the task function
        result: Task result (string or dict)
        status: Task status (SUCCESS, FAILURE, etc.)
        core_api: CoreApi instance for making API calls
    """
    task_data = {
        "id": job_id,
        "task": task_name,
        "result": result,
        "status": status,
    }

    response = core_api.api_put("/worker/task-results", task_data)
    if not response:
        logger.warning(f"Failed to save task result for {job_id}")
