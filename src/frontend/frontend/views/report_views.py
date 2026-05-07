from typing import Any

from flask import Response, abort, make_response, render_template, request, url_for
from flask.typing import ResponseReturnValue
from models.assess import Story
from models.report import ReportItem, ReportItemAttributeGroup, ReportTypes
from models.revision_diff import build_report_revision_diff_payload
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from frontend.auth import auth_required
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_count, render_datetime
from frontend.log import logger
from frontend.utils.form_data_parser import parse_formdata
from frontend.utils.validation_helpers import format_pydantic_errors
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
    def _get_story_attributes(grouped_attributes: list[ReportItemAttributeGroup]):
        story_attributes = []
        used_story_ids = []
        for ag in grouped_attributes:
            for attribute in ag.attributes:
                if not attribute.type or attribute.type != "STORY":
                    continue
                story_attributes.append(attribute)
                used_story_ids.extend(story_id.strip() for story_id in str(attribute.value).split(",") if story_id and story_id.strip())
        return story_attributes, list(dict.fromkeys(used_story_ids))

    @staticmethod
    def _normalize_request_attribute_value(value: Any) -> str | None:
        if isinstance(value, list):
            filtered = [str(item) for item in value if item]
            return ",".join(filtered)
        if value is None:
            return None
        return str(value)

    @staticmethod
    def _coerce_report_type_id(value: Any) -> Any:
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return value

    @classmethod
    def _apply_request_values_to_report(cls, report: ReportItem | None) -> ReportItem | None:
        if report is None:
            return None

        submitted_data = parse_formdata(request.values)
        if not submitted_data:
            return report

        if title := submitted_data.get("title"):
            report.title = title
        if report_item_type_id := submitted_data.get("report_item_type_id"):
            report.report_item_type_id = cls._coerce_report_type_id(report_item_type_id)

        submitted_attributes = submitted_data.get("attributes", {})
        if isinstance(submitted_attributes, dict):
            for group in report.grouped_attributes or []:
                for attribute in group.attributes:
                    if attribute.id is None:
                        continue
                    attribute_key = str(attribute.id)
                    if attribute_key not in submitted_attributes:
                        continue
                    attribute.value = cls._normalize_request_attribute_value(submitted_attributes[attribute_key])

        return report

    @classmethod
    def get_extra_context(cls, base_context: dict[str, Any]) -> dict[str, Any]:
        try:
            dpl = DataPersistenceLayer()
            report_types = dpl.get_objects(ReportTypes)
            base_context["report_types"] = report_types
            layout = request.args.get("layout") or request.form.get("layout") or base_context.get("layout", "split")
            report = cls._apply_request_values_to_report(base_context.get("report"))
            base_context["report"] = report
            base_context["story_attributes"] = []
            base_context["used_story_ids"] = []

            if report := base_context.get("report"):
                if report.grouped_attributes:
                    base_context["story_attributes"], base_context["used_story_ids"] = ReportItemView._get_story_attributes(
                        report.grouped_attributes
                    )

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
    def get_create_context(cls) -> dict[str, Any]:
        context = super().get_create_context()
        report = context.get("report")
        if not report:
            return context
        if story_ids := request.args.getlist("story_ids"):
            report.stories = [s for s in DataPersistenceLayer().get_objects(Story) if s.id in story_ids]
        context["report"] = cls._apply_request_values_to_report(report)

        return context

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

    def post(self, *args, **kwargs) -> tuple[str, int] | ResponseReturnValue:
        return self.update_view(object_id=0)

    def put(self, **kwargs) -> tuple[str, int] | ResponseReturnValue:
        object_id = self._get_object_id(kwargs)
        if object_id is None:
            return abort(405)
        return self.update_view(object_id=object_id)

    @classmethod
    def update_view(cls, object_id: int | str = 0):
        core_response, error = cls.process_form_data(object_id)
        response_object_id, model_instance, response_message = cls.resolve_update_response(object_id, core_response)
        if not core_response or error:
            return render_template(
                cls.get_update_template(),
                **cls.get_update_context(
                    object_id,
                    error=error,
                    model_instance=model_instance,
                    response_message=response_message,
                    form_action_object_id=response_object_id,
                ),
            ), 400

        notification_response = cls.render_response_notification(core_response)
        response = notification_response + render_template(
            cls.get_update_template(),
            **cls.get_update_context(
                object_id,
                error=error,
                model_instance=model_instance,
                response_message=response_message,
                form_action_object_id=response_object_id,
            ),
        )
        flask_response = make_response(response, 200)
        flask_response.headers["HX-Push-Url"] = cls.get_edit_route(**{cls._get_object_key(): core_response.get("id", object_id)})
        return flask_response

    @staticmethod
    def _parse_form_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
        return {key: ",".join(id for id in value if id) if isinstance(value, list) else value for key, value in attributes.items()}

    @classmethod
    def process_form_data(cls, object_id: int | str):
        try:
            form_data = parse_formdata(request.form)
            logger.debug(f"Parsed form data: {form_data}")
            form_data.pop("layout", None)
            form_data["attributes"] = cls._parse_form_attributes(form_data.get("attributes", {}))
            return cls.store_form_data(form_data, object_id)
        except ValidationError as exc:
            logger.error(format_pydantic_errors(exc, cls.model))
            return None, format_pydantic_errors(exc, cls.model)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error storing form data: {str(exc)}")
            return None, str(exc)

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
