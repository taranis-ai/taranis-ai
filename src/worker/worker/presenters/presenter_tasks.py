from celery import Task
from base64 import b64encode
from requests.exceptions import ConnectionError

import worker.presenters
from worker.presenters.base_presenter import BasePresenter
from worker.log import logger
from worker.core_api import CoreApi


class PresenterTask(Task):
    name = "presenter_task"
    max_retries = 3
    priority = 8
    default_retry_delay = 60
    time_limit = 60

    def __init__(self):
        self.core_api = CoreApi()
        self.presenters = {
            "html_presenter": worker.presenters.HTMLPresenter(),
            "json_presenter": worker.presenters.JSONPresenter(),
            "pdf_presenter": worker.presenters.PDFPresenter(),
            "text_presenter": worker.presenters.TextPresenter(),
        }

    def get_product(self, product_id: int) -> dict[str, str]:
        product = None
        try:
            product = self.core_api.get_product(product_id)
        except ConnectionError as e:
            raise ValueError(f"Unable to connect to core API: {e}") from e

        if not product:
            raise ValueError(f"Product with id {product_id} not found")

        return product

    def get_template(self, presenter: int) -> str:
        try:
            template = self.core_api.get_template(presenter)
        except ConnectionError as e:
            raise ValueError(f"Unable to connect to core API: {e}") from e

        if not template:
            raise ValueError(f"Template with id {presenter} not found")
        return template

    def get_presenter(self, product) -> BasePresenter:
        presenter_type = product.get("type")
        if not presenter_type:
            raise ValueError(f"Product {product['id']} has no presenter_type")

        if presenter := self.presenters.get(presenter_type):
            return presenter

        raise ValueError(f"Presenter {presenter_type} not implemented")

    def run(self, product_id: int):
        product = self.get_product(product_id)

        presenter = self.get_presenter(product)

        type_id: int = int(product["type_id"])
        template = self.get_template(type_id)

        logger.info(f"Rendering product {product_id} with presenter {presenter.type}")

        if rendered_product := presenter.generate(product, template):
            if isinstance(rendered_product, str):
                rendered_product = b64encode(rendered_product.encode("utf-8")).decode("ascii")
            else:
                rendered_product = b64encode(rendered_product).decode("ascii")

            return {"product_id": product_id, "message": f"Product: {product_id} rendered successfully", "render_result": rendered_product}

        raise ValueError(f"Presenter {presenter.type} returned no content")
