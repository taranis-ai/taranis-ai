from __future__ import annotations

from typing import Any

from core.log import logger
from core.managers import asset_manager, queue_manager
from core.managers.db_manager import db
from core.managers.sse_manager import sse_manager
from core.model.product import Product
from core.model.product_type import ProductType
from core.model.publisher_preset import PublisherPreset
from core.model.report_item import ReportItem
from core.model.story import Story
from core.model.user import User
from core.service.report_story_sync import ReportStorySyncService


class ReportPublishWorkflowService:
    @classmethod
    def create_and_publish(cls, data: dict, user: User | None):
        if not isinstance(data, dict):
            return {"error": "Invalid request payload"}, 400

        report_data = data.get("report")
        product_data = data.get("product")
        if not isinstance(report_data, dict) or not isinstance(product_data, dict):
            return {"error": "report and product objects are required"}, 400

        try:
            report_item, status = cls._create_report(report_data, user)
            if status != 200:
                db.session.rollback()
                return report_item, status

            product, status = cls._create_product(product_data, report_item)
            if status != 200:
                db.session.rollback()
                return product, status

            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Failed to create report and product workflow")
            return {"error": "Failed to create report and product"}, 500

        asset_manager.report_item_changed(report_item)
        sse_manager.report_item_updated(report_item.id)

        publish_result, publish_status = queue_manager.queue_manager.autopublish_product(product.id, product.default_publisher)
        response = cls._build_response(report_item, product, publish_result, publish_status)
        if publish_status != 200:
            return response, 500
        return response, 201

    @classmethod
    def _create_report(cls, data: dict[str, Any], user: User | None):
        report_payload = dict(data)
        attribute_overrides = report_payload.pop("attribute_overrides", [])
        if "story_ids" in report_payload and "stories" not in report_payload:
            report_payload["stories"] = report_payload.pop("story_ids")

        sanitized_report, error = ReportItem._sanitize_create_payload(report_payload)
        if error:
            return error
        if not sanitized_report:
            return {"error": "Invalid report payload"}, 400

        story_ids = sanitized_report.get("stories", [])
        stories, missing_story_ids = cls._get_stories(story_ids)
        if missing_story_ids:
            return {"error": "Story ids not found", "story_ids": missing_story_ids}, 400

        report_item = ReportItem.from_dict(sanitized_report)
        if user and not report_item.access_allowed(user, True):
            return {"error": f"User {user.id} is not allowed to create Report {report_item.id}"}, 403

        if user:
            report_item.user_id = user.id

        report_item.stories = stories
        report_item.add_attributes()

        override_error = cls._apply_attribute_overrides(report_item, attribute_overrides)
        if override_error:
            return override_error

        db.session.add(report_item)
        db.session.flush()
        if stories:
            ReportStorySyncService.sync_report_membership(report_item, stories, "attach")
        report_item.record_revision(user, note="created")

        return report_item, 200

    @classmethod
    def _create_product(cls, data: dict[str, Any], report_item: ReportItem):
        if not isinstance(data, dict):
            return {"error": "Invalid product payload"}, 400

        title = ReportItem._clean_title(data.get("title"))
        if title is None:
            return {"error": "Product title is required"}, 400

        product_type_id = cls._parse_int(data.get("product_type_id"))
        if product_type_id is None:
            return {"error": "product_type_id must be an integer"}, 400

        product_type = ProductType.get(product_type_id)
        if not product_type:
            return {"error": "Product type not found"}, 404

        supported_report_type_ids = {report_type.id for report_type in product_type.report_types if report_type}
        if report_item.report_item_type_id not in supported_report_type_ids:
            return {"error": "Selected product type does not support the selected report type"}, 400

        default_publisher = data.get("default_publisher")
        if not isinstance(default_publisher, str) or not default_publisher.strip():
            return {"error": "Invalid publisher preset value"}, 400

        publisher_preset = PublisherPreset.get(default_publisher.strip())
        if not publisher_preset:
            return {"error": "Publisher preset not found"}, 404

        description = data.get("description")
        if description is None:
            description = ""
        elif not isinstance(description, str):
            return {"error": "description must be a string"}, 400

        product = Product(
            title=title,
            product_type_id=product_type.id,
            description=description,
            auto_publish=True,
            default_publisher=publisher_preset.id,
        )
        product.report_items = [report_item]
        db.session.add(product)
        db.session.flush()
        return product, 200

    @staticmethod
    def _parse_int(value: Any) -> int | None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    @staticmethod
    def _get_stories(story_ids: list[str]) -> tuple[list[Story], list[str]]:
        stories = Story.get_bulk(story_ids) if story_ids else []
        found_story_ids = {story.id for story in stories}
        missing_story_ids = [story_id for story_id in story_ids if story_id not in found_story_ids]
        return stories, missing_story_ids

    @classmethod
    def _apply_attribute_overrides(cls, report_item: ReportItem, overrides: list[dict]):
        if overrides is None:
            return None
        if not isinstance(overrides, list):
            return {"error": "attribute_overrides must be a list"}, 400

        for override in overrides:
            normalized_override, error = cls._normalize_override(override)
            if error:
                return error
            if normalized_override is None:
                return {"error": "Invalid attribute override"}, 400

            matches = [
                attribute
                for attribute in report_item.attributes
                if attribute.group_title == normalized_override["group_title"] and attribute.title == normalized_override["title"]
            ]
            if not matches:
                return {
                    "error": f"Attribute override target not found for group '{normalized_override['group_title']}' and title '{normalized_override['title']}'"
                }, 400
            if len(matches) > 1:
                return {
                    "error": f"Attribute override target is ambiguous for group '{normalized_override['group_title']}' and title '{normalized_override['title']}'"
                }, 400
            matches[0].value = normalized_override["value"]

        return None

    @staticmethod
    def _normalize_override(override: Any):
        if not isinstance(override, dict):
            return None, ({"error": "Each attribute override must be an object"}, 400)

        group_title = override.get("group_title")
        if not isinstance(group_title, str):
            return None, ({"error": "attribute override group_title must be a string"}, 400)

        title = ReportItem._clean_title(override.get("title"))
        if title is None:
            return None, ({"error": "attribute override title is required"}, 400)

        if "value" not in override:
            return None, ({"error": "attribute override value is required"}, 400)

        value = override.get("value")
        return {
            "group_title": group_title,
            "title": title,
            "value": value if isinstance(value, str) else str(value),
        }, None

    @staticmethod
    def _build_response(report_item: ReportItem, product: Product, publish_result: dict[str, Any], publish_status: int) -> dict[str, Any]:
        publish_payload = {
            "status": "scheduled" if publish_status == 200 else "failed",
            "publisher_id": product.default_publisher,
        }
        if publish_status == 200:
            publish_payload["message"] = publish_result.get("message")
            message = "Report and product created; publish scheduled"
        else:
            publish_payload["error"] = publish_result.get("error")
            message = "Report and product created; publish scheduling failed"

        return {
            "message": message,
            "report": ReportPublishWorkflowService._serialize_report(report_item),
            "product": ReportPublishWorkflowService._serialize_product(product),
            "publish": publish_payload,
        }

    @staticmethod
    def _serialize_report(report_item: ReportItem) -> dict[str, Any]:
        data = report_item.to_detail_dict()
        data["attributes"] = [attribute.to_report_dict() for attribute in report_item.attributes]
        return data

    @staticmethod
    def _serialize_product(product: Product) -> dict[str, Any]:
        data = product.to_detail_dict()
        data["auto_publish"] = product.auto_publish
        data["default_publisher"] = product.default_publisher
        return data
