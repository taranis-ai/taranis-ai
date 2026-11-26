import hashlib
import mimetypes
import re
import unicodedata
from datetime import UTC, datetime
from typing import Any

from models.product import WorkerProduct as Product

from worker.core_api import CoreApi
from worker.log import logger


class BasePublisher:
    _REMOTE_TITLE_MAX_BYTES = 160
    _REMOTE_FILE_NAME_MAX_BYTES = 240

    def __init__(self):
        self.type = "BASE_PUBLISHER"
        self.name = "Base Publisher"
        self.description = "Base abstract type for all publishers"
        self.file_name: str = f"Taranis_product_{datetime.now(UTC).strftime('%d-%m-%Y_%H-%M')}"
        self.core_api = CoreApi()

    def publish(self, publisher: dict[str, Any], product: dict[str, Any], rendered_product: Product) -> Any:
        raise NotImplementedError

    def print_exception(self, error):
        logger.error(f"Publishing failed: type={self.type} exception_type={type(error).__name__}")

    def set_file_name(self, product):
        self.file_name = BasePublisher.get_file_name(product)

    def set_safe_remote_file_name(self, product):
        self.file_name = BasePublisher.get_safe_remote_file_name(product)

    @staticmethod
    def get_file_name(product) -> str:
        product_title = product.get("title")
        mime_type = product.get("mime_type")

        file_extension = mimetypes.guess_extension(mime_type, strict=False) or ""
        return f"{product_title}_{datetime.now(UTC).strftime('%d-%m-%Y_%H-%M')}{file_extension}"

    @classmethod
    def get_safe_remote_file_name(cls, product) -> str:
        product_title = cls._safe_remote_title(product.get("title"))
        mime_type = product.get("mime_type")
        file_extension = mimetypes.guess_extension(mime_type, strict=False) or ""
        file_name = f"{product_title}_{datetime.now(UTC).strftime('%d-%m-%Y_%H-%M')}{file_extension}"
        return cls._require_safe_remote_file_name(file_name)

    @classmethod
    def _safe_remote_title(cls, product_title: Any) -> str:
        raw_title = str(product_title or "")
        normalized_title = unicodedata.normalize("NFKC", raw_title)
        safe_title = "".join(character if character.isalnum() or character in " -_" else "_" for character in normalized_title)
        safe_title = re.sub(r"_+", "_", safe_title).strip(" _") or "Taranis_product"

        safe_title_bytes = safe_title.encode("utf-8")
        needs_digest = safe_title != raw_title or len(safe_title_bytes) > cls._REMOTE_TITLE_MAX_BYTES
        digest_suffix = ""
        if needs_digest:
            digest = hashlib.sha256(raw_title.encode("utf-8", errors="replace")).hexdigest()[:12]
            digest_suffix = f"_{digest}"

        prefix_byte_limit = cls._REMOTE_TITLE_MAX_BYTES - len(digest_suffix)
        safe_title = safe_title_bytes[:prefix_byte_limit].decode("utf-8", errors="ignore").rstrip(" _")
        return f"{safe_title}{digest_suffix}"

    @classmethod
    def _require_safe_remote_file_name(cls, file_name: str) -> str:
        normalized_file_name = unicodedata.normalize("NFKC", file_name)
        if (
            not file_name
            or normalized_file_name != file_name
            or file_name in {".", ".."}
            or "/" in file_name
            or "\\" in file_name
            or any(unicodedata.category(character).startswith("C") for character in file_name)
            or len(file_name.encode("utf-8")) > cls._REMOTE_FILE_NAME_MAX_BYTES
        ):
            raise ValueError("Remote file name must be a safe, normalized basename")
        return file_name

    def _extract_parameters(self, publisher: dict[str, Any]) -> dict[str, Any]:
        return publisher.get("parameters") or {}

    @staticmethod
    def _require_rendered_data(rendered_product: Product) -> bytes:
        if rendered_product.data is None:
            raise ValueError("Rendered product data is required")
        return rendered_product.data
