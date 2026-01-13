import contextlib
from typing import Any

from flask import Response, make_response
from models.types import PRESENTER_TYPES, PUBLISHER_TYPES
from sqlalchemy import select

from core.log import logger
from core.managers import queue_manager
from core.managers.db_manager import db
from core.model.product import Product
from core.model.product_type import ProductType
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
    def get_publisher(publisher_name: str) -> PublisherPreset:
        filter_query = PublisherPreset.get_filter_query(filter_args={"search": publisher_name})
        if publisher := PublisherPreset.get_first(filter_query):
            return publisher
        else:
            raise ValueError(f"No publisher preset found with name like '{publisher_name}")

    @staticmethod
    def create_product_type(
        mimetype: str,
        *,
        description: str = "",
    ) -> ProductType:
        mapping: dict[str, tuple[str, PRESENTER_TYPES, str | None]] = {
            "application/json": ("Json Presenter", PRESENTER_TYPES.JSON_PRESENTER, "impact_assessment_json_template.json"),
            "application/pdf": ("Pdf Presenter", PRESENTER_TYPES.PDF_PRESENTER, "impact_assessment_pdf_template.html"),
            "application/stix": ("Stix Presenter", PRESENTER_TYPES.STIX_PRESENTER, None),
            "text/html": ("Html Presenter", PRESENTER_TYPES.HTML_PRESENTER, "impact_assessment_html_template.html"),
            "text/plain": ("Text Presenter", PRESENTER_TYPES.TEXT_PRESENTER, "impact_assessment_text_template.txt"),
        }

        title, presenter_type, template = mapping.get(
            mimetype,
            ("Text Presenter", PRESENTER_TYPES.TEXT_PRESENTER, "impact_assessment_text_template.txt"),
        )

        if impact_assessment_type := ReportItemType.get_by_title("Impact Assessment"):
            parameters = {"TEMPLATE_PATH": template} if template else {}

            return ProductType.add(
                {
                    "title": title,
                    "type": presenter_type,
                    "description": description,
                    "parameters": parameters,
                    "report_types": [impact_assessment_type.id],
                }
            )
        else:
            raise ValueError("Impact Assessment type not found")

    @staticmethod
    def cti_endpoint(data: dict[str, Any], headers: dict[str, Any], query_params: dict[str, Any]) -> Response:
        report = None
        product_type = None
        product = None

        publisher_name = query_params.get("publisher")
        if not publisher_name:
            return make_response(
                {"status": "error", "message": "No publisher selcted. Use ?publisher=<publisher_name>"},
                400,
            )

        try:
            publisher = CTIService.get_publisher(publisher_name)
        except ValueError as e:
            return make_response(
                {"status": "error", "message": str(e)},
                400,
            )
        try:
            report = CTIService.create_cti_report(data)

            mimetype = headers.get("Accept", "text/plain")
            product_type = CTIService.create_product_type(mimetype)

            product_data = {
                "title": data.get("title"),
                "description": "",
                "product_type_id": product_type.id,
                "auto_publish": True,
                "default_publisher": publisher.id,
            }

            product = CTIService.create_product(product_data, report)

            if publisher_result := queue_manager.queue_manager.autopublish_product_sync(
                product.id,
                publisher.id,
            ):
                return make_response(
                    {"status": "success", "result": publisher_result},
                    200,
                )

            else:
                return make_response(
                    {"status": "error", "message": "Failed to publish product"},
                    500,
                )

        except Exception:
            logger.exception("Error creating CTI report / product")
            return make_response(
                {"status": "error", "message": "Internal server error"},
                500,
            )

        finally:
            with contextlib.suppress(Exception):
                db.session.rollback()
            try:
                if product is not None:
                    db.session.delete(product)

                if product_type is not None:
                    db.session.delete(product_type)

                if report is not None:
                    db.session.delete(report)

                db.session.commit()
            except Exception:
                db.session.rollback()
                logger.exception("Cleanup failed in CTI endpoint")
