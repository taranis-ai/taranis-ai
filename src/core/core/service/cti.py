from typing import Any

from flask import Response, make_response

from core.log import logger
from core.managers.queue_manager import queue_manager
from core.model.product import Product
from core.model.publisher_preset import PublisherPreset
from core.model.report_item import ReportItem
from core.model.report_item_type import ReportItemType


class CTIService:
    @staticmethod
    def create_cti_report(data: dict[str, Any]) -> ReportItem:
        impact_assessment_type = ReportItemType.get_by_title("Impact Assessment")
        if not impact_assessment_type:
            raise ValueError("Impact Assessment type not found")
        data["type"] = impact_assessment_type.id
        return ReportItem.add(data)[0]

    @staticmethod
    def create_product(data: dict[str, Any], report: ReportItem) -> Product:
        data["report_id"] = report.id
        return Product.add(data)

    @staticmethod
    def get_publisher(data: dict[str, Any]) -> PublisherPreset:
        if publisher := PublisherPreset.get(data["publisher_id"]):
            return publisher
        raise ValueError("Publisher not found")

    @staticmethod
    def cti_endpoint(data: dict[str, Any]) -> Response:
        try:
            report = CTIService.create_cti_report(data)
            product = CTIService.create_product(data, report)
            publisher = CTIService.get_publisher(data)
            if publisher_result := queue_manager.autopublish_product_sync(product.id, publisher.id):
                if publisher_result.status_code == 200:
                    return make_response({"status": "success"}, 200)
                else:
                    return make_response({"status": "error", "message": "Failed to publish product"}, publisher_result.status_code)
            else:
                return make_response({"status": "error", "message": "Failed to publish product"}, 500)
        except Exception:
            logger.exception("Error creating CTI report")
            return make_response({"status": "error", "message": "Internal server error"}, 500)
