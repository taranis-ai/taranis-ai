from base64 import b64decode
from pathlib import Path
from tempfile import NamedTemporaryFile

from flask import Response, current_app, send_file
from models.product import validate_linkable_url
from sqlalchemy import select

from core.log import logger
from core.managers import queue_manager
from core.managers.db_manager import db
from core.model.product import Product
from core.model.report_item import ReportItem
from core.model.task import Task


class ProductService:
    PUBLISHED_REPORTS_FOLDER = "published-reports"

    @classmethod
    def _published_reports_directory(cls) -> Path:
        return Path(current_app.config["DATA_FOLDER"]).resolve() / cls.PUBLISHED_REPORTS_FOLDER

    @classmethod
    def get_render(cls, product_id: str):
        render_error = Task.get_latest_matching(
            exact_ids={product_id, f"presenter_task_{product_id}"},
            prefixes=[f"presenter_task_{product_id}_"],
            task_name="presenter_task",
        )
        if render_error and render_error.status == "FAILURE":
            logger.error(f"Failed to render product {product_id}: {render_error.to_dict()}")
            return {"error": render_error.result}, 200
        if product_data := Product.get_render(product_id):
            binary = b64decode(product_data["blob"])
            return Response(
                binary,
                mimetype=product_data["mime_type"],
                headers={"Content-Disposition": f'attachment; filename="{product_data["filename"]}"'},
                status=200,
            )
        return {"error": "Product not found"}, 404

    @classmethod
    def publish_to_taranis(cls, product_id: str):
        product = Product.get(product_id)
        if not product or not product.render_result:
            return {"error": "Rendered product not found"}, 404

        report_directory = cls._published_reports_directory()
        report_directory.mkdir(parents=True, exist_ok=True)
        report_path = report_directory / product.id

        temporary_path = None
        try:
            with NamedTemporaryFile(dir=report_directory, delete=False) as temporary_file:
                temporary_file.write(b64decode(product.render_result))
                temporary_path = Path(temporary_file.name)
            temporary_path.replace(report_path)
        finally:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)

        application_root = current_app.config["APPLICATION_ROOT"].rstrip("/")
        public_url = validate_linkable_url(f"{application_root}/reports/{product.id}")
        product.last_published_url = public_url
        db.session.commit()
        return {"message": f"Product published at {public_url}", "url": public_url}, 200

    @classmethod
    def get_published_report(cls, product_id: str):
        if not (product := Product.get(product_id)):
            return {"error": "Published report not found"}, 404

        report_path = cls._published_reports_directory() / product.id
        if not report_path.is_file():
            return {"error": "Published report not found"}, 404

        response = send_file(report_path, mimetype=product.product_type.get_mimetype(), conditional=True)
        response.headers["Content-Security-Policy"] = "sandbox allow-scripts allow-downloads"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @classmethod
    def autopublish_product(cls, report_item_id: str, user_id: str | None = None):
        products = ProductService.get_products_for_auto_render(report_item_id)
        for product in products:
            if not product.default_publisher:
                logger.warning(f"Product {product.id} is set to auto publish but has no default publisher")
                continue
            result, status = queue_manager.queue_manager.autopublish_product(product.id, product.default_publisher, user_id=user_id)
            if status != 200:
                logger.error(
                    "Failed to schedule autopublish jobs for product %s: %s",
                    product.id,
                    result.get("error", "unknown error"),
                )
        return products

    @classmethod
    def get_products_for_auto_render(cls, report_item_id: str) -> list[Product]:
        stmt = select(Product).join(Product.report_items).where(Product.auto_publish.is_(True), ReportItem.id == report_item_id).distinct()
        return list(db.session.scalars(stmt).all())
