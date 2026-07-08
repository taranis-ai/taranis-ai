from typing import Any

from flask import Response, abort, make_response, render_template, request, url_for
from flask.typing import ResponseReturnValue
from models.assess import Story
from models.cti import CTIResponse
from models.product import Product, ProductType
from models.report import ReportItem, ReportTypes
from models.revision_diff import build_report_revision_diff_payload
from werkzeug.exceptions import Forbidden, HTTPException

from frontend.auth import auth_required
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_count, render_datetime
from frontend.log import logger
from frontend.utils.form_data_parser import parse_formdata
from frontend.views.base_view import BaseView


class ReportItemView(BaseView):
    model = ReportItem
    icon = "presentation-chart-bar"
    htmx_list_template = "analyze/report_table.html"
    htmx_update_template = "analyze/report.html"
    edit_template = "analyze/report_view.html"
    default_template = "analyze/index.html"

    base_route = "analyze.analyze"
    edit_route = "analyze.report"

    @classmethod
    def get_form_action(cls, object_id: str = "0") -> str:
        return cls.get_edit_route(report_id=object_id)

    @classmethod
    def _get_object_key(cls) -> str:
        return "report_id"

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Title", "field": "title", "sortable": True, "renderer": None},
            {"title": "Created", "field": "created", "sortable": True, "renderer": render_datetime, "render_args": {"field": "created"}},
            {"title": "Type", "field": "report_item_type", "sortable": False, "renderer": None},
            {
                "title": "Stories",
                "field": "stories",
                "sortable": True,
                "renderer": render_count,
                "render_args": {"field": "stories"},
            },
        ]

    @staticmethod
    def _normalize_attribute_value(value: Any) -> str:
        if isinstance(value, list):
            return ",".join(str(item) for item in value if item)
        return "" if value is None else str(value)

    @staticmethod
    def _normalize_layout(layout: Any) -> str:
        return layout if layout in {"split", "stacked"} else "split"

    @staticmethod
    def _strip_layout_keys(data: dict[str, Any]) -> dict[str, Any]:
        data.pop("layout", None)
        data.pop("layout_switch", None)
        return data

    @classmethod
    def _parse_form_attributes(cls, attributes: dict[str, Any]) -> dict[str, Any]:
        return {key: cls._normalize_attribute_value(value) for key, value in attributes.items()}

    @staticmethod
    def _normalize_story_ids(stories: Any, remove_story_id: str | None = None, remove_all: bool = False) -> list[str]:
        if remove_all:
            return []

        story_ids = stories if isinstance(stories, list) else ([stories] if stories else [])
        normalized_story_ids = [str(story_id) for story_id in story_ids if story_id]
        if remove_story_id:
            normalized_story_ids = [story_id for story_id in normalized_story_ids if story_id != remove_story_id]
        return normalized_story_ids

    @classmethod
    def _normalize_form_data(cls, form_data: dict[str, Any]) -> dict[str, Any]:
        form_data = dict(form_data)
        cls._strip_layout_keys(form_data)

        if story_ids := form_data.pop("story_ids", None):
            form_data.setdefault("stories", story_ids)

        remove_story_id = form_data.pop("remove_story_id", None)
        remove_all_stories = form_data.pop("remove_all_stories", None) == "1"
        if "stories" in form_data or remove_story_id or remove_all_stories:
            form_data["stories"] = cls._normalize_story_ids(form_data.get("stories"), remove_story_id, remove_all_stories)

        attributes = form_data.get("attributes", {})
        form_data["attributes"] = cls._parse_form_attributes(attributes if isinstance(attributes, dict) else {})

        return cls.model.model_validate(form_data).model_dump(exclude_unset=True)

    @classmethod
    def _get_normalized_form_data_from(cls, submitted_data: Any) -> dict[str, Any]:
        form_data = parse_formdata(submitted_data)
        if story_ids := submitted_data.getlist("story_ids"):
            form_data["story_ids"] = story_ids
        return cls._normalize_form_data(form_data)

    @classmethod
    def _get_normalized_form_data(cls) -> dict[str, Any]:
        return cls._get_normalized_form_data_from(request.form)

    @classmethod
    def _get_normalized_request_values(cls) -> dict[str, Any]:
        return cls._get_normalized_form_data_from(request.values)

    @classmethod
    def _apply_form_data_to_report(cls, report: ReportItem, form_data: dict[str, Any]) -> ReportItem:
        if "title" in form_data:
            report.title = form_data["title"]
        if "report_item_type_id" in form_data:
            report.report_item_type_id = form_data["report_item_type_id"]

        if isinstance(form_data.get("attributes"), dict):
            for group in report.grouped_attributes or []:
                for attribute in group.attributes:
                    if attribute.id is None:
                        continue
                    attribute_key = str(attribute.id)
                    if attribute_key not in form_data["attributes"]:
                        continue
                    attribute.value = form_data["attributes"][attribute_key]

        return report

    @classmethod
    def _apply_story_ids_to_report(cls, report: ReportItem, story_ids: Any) -> None:
        normalized_story_ids = set(cls._normalize_story_ids(story_ids))
        report.stories = [story for story in DataPersistenceLayer().get_objects(Story) if str(story.id) in normalized_story_ids]

    @classmethod
    def get_extra_context(cls, base_context: dict[str, Any]) -> dict[str, Any]:
        try:
            dpl = DataPersistenceLayer()
            report_types = dpl.get_objects(ReportTypes)
            base_context["report_types"] = report_types
            base_context["current_search"] = request.args.get("search", "")
            base_context["current_completed_filter"] = request.args.get("completed", "")
            base_context["current_report_item_type_filter"] = request.args.get("report_item_type_id", "")
            layout = cls._normalize_layout(request.values.get("layout_switch") or request.values.get("layout") or base_context.get("layout"))

            report = base_context.get("report")
            if report:
                if cls.is_create_object_id(report.id):
                    base_context["existing_products"] = []
                else:
                    product_types = {product_type.id: product_type.title for product_type in dpl.get_objects(ProductType)}
                    products = dpl.get_objects(Product)
                    base_context["existing_products"] = [
                        {
                            "id": product.id,
                            "name": f"{product.title} ({product_types.get(product.product_type_id, 'Unknown')})",
                        }
                        for product in products
                        if product.id
                    ]
                submitted_data = cls._get_normalized_request_values()
                report = cls._apply_form_data_to_report(report, submitted_data)
                if cls.is_create_object_id(report.id) and (story_ids := submitted_data.get("stories")):
                    cls._apply_story_ids_to_report(report, story_ids)
                base_context["report"] = report
            else:
                base_context["existing_products"] = []

            base_context |= {
                "layout": layout,
                "actions": cls.get_report_actions(),
            }
        except HTTPException:
            raise
        except Exception:
            logger.exception("Error getting extra context for ReportItemView")

        return base_context

    @classmethod
    def _render_layout_switch_view(cls, object_id: str = "0") -> tuple[str, int]:
        if cls.is_create_object_id(object_id):
            return render_template(cls.get_update_template(), **cls.get_create_context()), 200

        report = cls.get_object_by_id(object_id)
        if not report:
            return abort(404)

        return (
            render_template(
                cls.get_update_template(),
                **cls.get_update_context(object_id, model_instance=report, form_action_object_id=object_id),
            ),
            200,
        )

    @classmethod
    def get_report_actions(cls) -> list[dict[str, Any]]:
        return [
            {
                "label": "Clone Report",
                "icon": "document-duplicate",
                "method": "post",
                "url": url_for("analyze.clone_report", report_id=""),
                "hx_target": f"#{cls.model_name()}-table-container",
                "hx_swap": "outerHTML",
            },
            {"label": "Edit", "class": "btn-primary", "icon": "pencil-square", "url": url_for(cls.edit_route, report_id=""), "type": "link"},
            {
                "label": "Delete",
                "icon": "trash",
                "class": "btn-error",
                "method": "delete",
                "url": url_for(cls.edit_route, report_id=""),
                "hx_target_error": "#notification-bar",
                "hx_target": f"#{cls.model_name()}-table-container",
                "hx_swap": "outerHTML",
                "type": "button",
                "confirm": "Are you sure you want to delete this item?",
            },
        ]

    @staticmethod
    @auth_required()
    def clone_report(report_id: str) -> tuple[str, int] | ResponseReturnValue:
        if not report_id:
            return abort(400, description="No report ID provided for cloning.")
        CoreApi().clone_report(report_id)
        return ReportItemView.list_view()

    @staticmethod
    @auth_required()
    def cti_dialog(report_id: str) -> tuple[str, int]:
        payload = CoreApi().api_get(f"/analyze/report-items/{report_id}/cti") or {"item_type": "report", "item_id": report_id, "iocs": []}
        return render_template("shared/cti_dialog.html", cti=CTIResponse.model_validate(payload)), 200

    @staticmethod
    @auth_required()
    def trigger_bot_action(report_id: str | None = None) -> ResponseReturnValue:
        bot_id = request.form.get("bot_id")
        if not bot_id:
            return make_response(ReportItemView.render_response_notification({"error": "Bot identifier is required."}), 400)
        if report_id:
            payload = {"report_id": report_id, "bot_id": bot_id}
        elif report_ids := request.form.getlist("report_ids"):
            payload = {"report_ids": report_ids, "bot_id": bot_id}
        else:
            return make_response(ReportItemView.render_response_notification({"error": "No reports selected for bot action."}), 400)

        response = CoreApi().api_post("/analyze/report-items/botactions", json_data=payload)
        status = 200 if getattr(response, "ok", False) else 400
        return make_response(ReportItemView.get_notification_from_response(response), status)

    def post(self, *args: Any, **kwargs: Any) -> tuple[str, int] | ResponseReturnValue:
        object_id = self._get_object_id(kwargs) or "0"
        if request.form.get("layout_switch"):
            return self._render_layout_switch_view(object_id)
        return self.update_view_table(object_id=object_id)

    def put(self, **kwargs: Any) -> tuple[str, int] | ResponseReturnValue:
        object_id = self._get_object_id(kwargs)
        if object_id is None:
            return abort(405)
        return self.update_view_table(object_id=object_id)

    @staticmethod
    @auth_required()
    def versions_view(report_id: str) -> tuple[str, int] | Response:
        """Display revision history for a report"""
        if not report_id:
            return abort(400, description="No report ID provided.")

        # Get report data
        report = DataPersistenceLayer().get_object(ReportItem, report_id)
        if not report:
            return abort(404, description="Report not found.")

        # Get revisions from core API
        revisions_data = CoreApi().api_get(f"/analyze/report-items/{report_id}/revisions")
        revisions = revisions_data.get("items", []) if revisions_data else []

        context = {
            "report": report,
            "revisions": revisions,
        }

        return render_template("analyze/report_versions.html", **context), 200

    @classmethod
    def handle_submit_error(cls, object_id: str, error: str | None = None, resp_obj: dict[str, Any] | None = None) -> tuple[str, int]:
        return cls.render_submitted_form_error(object_id, error=error, resp_obj=resp_obj)

    @classmethod
    def handle_submit_success(cls, object_id: str, core_response: dict[str, Any]) -> ResponseReturnValue:
        cls.add_flash_notification(core_response)
        return cls.redirect_htmx(cls.get_submit_redirect_target(object_id, core_response))

    @classmethod
    def get_submit_redirect_target(cls, object_id: str, core_response: dict[str, Any]) -> str:
        response_object_id = core_response.get("id", object_id)
        if not cls.is_create_object_id(object_id):
            try:
                if cls.get_object_by_id(response_object_id) is None:
                    return cls.get_base_route()
            except Forbidden:
                return cls.get_base_route()
        target = cls.get_edit_route(report_id=response_object_id)
        if cls.is_create_object_id(object_id) and (layout := request.values.get("layout")):
            target = f"{target}?layout={layout}"
        return target

    @staticmethod
    @auth_required()
    def diff_view(report_id: str, from_rev: int, to_rev: int) -> tuple[str, int] | Response:
        """Display diff between two revisions"""
        if not report_id:
            return abort(400, description="No report ID provided.")

        core_api = CoreApi()
        from_revision = core_api.api_get(f"/analyze/report-items/{report_id}/revisions/{from_rev}")
        to_revision = core_api.api_get(f"/analyze/report-items/{report_id}/revisions/{to_rev}")
        if not from_revision or not to_revision:
            return abort(404, description="Revision not found.")

        report_title = to_revision.get("data", {}).get("title") or from_revision.get("data", {}).get("title")
        diff = build_report_revision_diff_payload(report_id, report_title, from_revision, to_revision)

        context = {
            "diff": diff,
            "from_rev": from_rev,
            "to_rev": to_rev,
            "report_id": report_id,
        }

        return render_template("analyze/report_diff.html", **context), 200
