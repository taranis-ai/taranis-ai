import mimetypes
from datetime import datetime

from worker.log import logger
from worker.core_api import CoreApi
from worker.types import Product


class BasePublisher:
    def __init__(self):
        self.type = "BASE_PUBLISHER"
        self.name = "Base Publisher"
        self.description = "Base abstract type for all publishers"
        self.file_name = None
        self.core_api = CoreApi()

    def publish(self, publisher: dict, product: dict, rendered_product: Product) -> str:
        raise NotImplementedError

    def print_exception(self, error):
        logger.exception(f"Publishing Failed: {self.type} - {error}")

    def set_file_name(self, product):
        product_title = product.get("title")
        mime_type = product.get("mime_type")

        file_extension = mimetypes.guess_extension(mime_type, strict=False)
        self.file_name = f"{product_title}_{datetime.now().strftime('%d-%m-%Y_%H-%M')}{file_extension}"
        logger.debug(f"{self.file_name=}")
