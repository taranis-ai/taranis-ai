from typing import Any

from flask import Response, make_response
from models.types import PUBLISHER_TYPES
from sqlalchemy import select

from core.log import logger
from core.managers import queue_manager
from core.managers.db_manager import db
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
        data["report_item_type_id"] = impact_assessment_type.id

        attributes = {
            "Properties": {
                "Assessment ID": data["assessment_id"],
                "Title": data["title"],
                "Author": data["author"],
                "Created": data["date_created"],
                "Summary": data["summary"],
                "Scope": data["scope"],
                "Methodology": data["methodology"],
                "Findings": data["findings"],
                "Recommendations": data["recommendations"],
                "Appendices": data.get("appendices", ""),
                "References": data.get("references", ""),
            }
        }

        report_item_data = {
            "title": data["title"],
            "report_item_type_id": impact_assessment_type.id,
        }

        report_item, status = ReportItem.add(report_item_data)
        if status != 200:
            raise RuntimeError("Failed to create Impact Assessment report")

        for attr in report_item.attributes:
            group = attr.group_title
            title = attr.title

            if group in attributes and title in attributes[group]:
                attr.value = attributes[group][title]

        db.session.commit()

        return report_item

    @staticmethod
    def create_product(data: dict[str, Any], report: ReportItem) -> Product:
        data["report_items"] = [report.id]
        return Product.add(data)

    @staticmethod
    def get_publisher() -> PublisherPreset:
        publisher = PublisherPreset.get_first(select(PublisherPreset).where(PublisherPreset.type == PUBLISHER_TYPES.S3_PUBLISHER))
        if not publisher:
            raise ValueError("No publisher preset found for Impact Assessment")
        return publisher

    @staticmethod
    def cti_endpoint(data: dict[str, Any]) -> Response:
        try:
            report = CTIService.create_cti_report(data)
            publisher = CTIService.get_publisher()

            product_data = {
                "title": data.get("title"),
                "description": "",
                "product_type_id": 8,
                "auto_publish": True,
                "default_publisher": publisher.id,
            }

            product = CTIService.create_product(product_data, report)

            publisher_result = queue_manager.queue_manager.autopublish_product_sync(
                product.id,
                publisher.id,
            )

            if publisher_result:
                return make_response(
                    {
                        "status": "success",
                        "result": publisher_result,
                    },
                    200,
                )

            return make_response(
                {"status": "error", "message": "Failed to publish product"},
                500,
            )

        except Exception:
            logger.exception("Error creating CTI report")
            return make_response(
                {"status": "error", "message": "Internal server error"},
                500,
            )
