from typing import Any

from flask import Response, abort, render_template, request, url_for
from flask.typing import ResponseReturnValue
from models.assess import Story
from models.report import ReportItem, ReportItemAttributeGroup, ReportTypes
from pydantic import ValidationError
from werkzeug.exceptions import Forbidden, HTTPException

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
    def submits_via_standard_form(cls) -> bool:
        return True

    @classmethod
    def get_form_action(cls, object_id: int | str = 0) -> str:
        if str(object_id) == "0":
            return cls.get_edit_route(report_id="0")
        return cls.get_edit_route(report_id=object_id)

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
    def _normalize_draft_attribute_value(value: Any) -> str:
        if isinstance(value, list):
            return ",".join(item for item in value if item)
        return "" if value is None else str(value)

    @classmethod
    def _apply_draft_query_state(cls, report: ReportItem | None) -> ReportItem | None:
        if report is None or request.method != "GET" or not request.args:
            return report

        parsed_args = parse_formdata(request.args)
        parsed_args.pop("layout", None)
        parsed_args.pop("current_layout", None)
        if not parsed_args:
            return report

        draft_report = report.model_copy(deep=True)

        if title := parsed_args.get("title"):
            draft_report.title = str(title)

        report_item_type_id = parsed_args.get("report_item_type_id")
        if report_item_type_id not in (None, ""):
            draft_report.report_item_type_id = str(report_item_type_id)

        draft_attributes = parsed_args.get("attributes")
        if isinstance(draft_attributes, dict) and draft_report.grouped_attributes:
            for group in draft_report.grouped_attributes:
                for attribute in group.attributes:
                    draft_value = draft_attributes.get(str(attribute.id))
                    if draft_value is not None:
                        attribute.value = cls._normalize_draft_attribute_value(draft_value)

        return draft_report

    @classmethod
    def get_extra_context(cls, base_context: dict[str, Any]) -> dict[str, Any]:
        try:
            dpl = DataPersistenceLayer()
            report_types = dpl.get_objects(ReportTypes)
            base_context["report_types"] = report_types
            base_context["current_search"] = request.args.get("search", "")
            base_context["current_completed_filter"] = request.args.get("completed", "")
            base_context["current_report_item_type_filter"] = request.args.get("report_item_type_id", "")
            layout = request.args.get("layout") or request.form.get("current_layout") or base_context.get("layout", "split")
            report = cls._apply_draft_query_state(base_context.get("report"))
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
                "standard_form_submit": cls.submits_via_standard_form(),
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
        if title := request.values.get("title"):
            report.title = title
        if report_item_type_id := request.values.get("report_item_type_id"):
            report.report_item_type_id = report_item_type_id
        if story_ids := request.args.getlist("story_ids"):
            report.stories = [s for s in DataPersistenceLayer().get_objects(Story) if s.id in story_ids]
            context["report"] = report

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
        return self.update_view_table(object_id=self._get_object_id(kwargs) or 0)

    def put(self, **kwargs) -> tuple[str, int] | ResponseReturnValue:
        object_id = self._get_object_id(kwargs)
        if object_id is None:
            return abort(405)
        return self.update_view_table(object_id=object_id)

    @staticmethod
    def _parse_form_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
        return {key: ",".join(id for id in value if id) if isinstance(value, list) else value for key, value in attributes.items()}

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
    def process_form_data(cls, object_id: int | str):
        try:
            form_data = parse_formdata(request.form)
            logger.debug(f"Parsed form data: {form_data}")
            form_data.pop("layout", None)
            form_data.pop("current_layout", None)
            remove_story_id = form_data.pop("remove_story_id", None)
            remove_all_stories = bool(form_data.pop("remove_all_stories", None))
            if "stories" in form_data or remove_story_id or remove_all_stories:
                form_data["stories"] = cls._normalize_story_ids(form_data.get("stories"), remove_story_id, remove_all_stories)
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

    @classmethod
    def handle_submit_error(cls, object_id: int | str, error: str | None = None, resp_obj: dict[str, Any] | None = None) -> tuple[str, int]:
        return cls.render_submitted_form_error(object_id, error=error, resp_obj=resp_obj)

    @classmethod
    def handle_submit_success(cls, object_id: int | str, core_response: dict[str, Any]) -> ResponseReturnValue:
        cls.add_flash_notification(core_response)
        return cls.redirect_htmx(cls.get_submit_redirect_target(object_id, core_response))

    @classmethod
    def get_submit_redirect_target(cls, object_id: int | str, core_response: dict[str, Any]) -> str:
        response_object_id = core_response.get("id", object_id)
        if not cls.is_create_object_id(object_id):
            try:
                if cls.get_object_by_id(response_object_id) is None:
                    return cls.get_base_route()
            except Forbidden:
                return cls.get_base_route()
        return cls.get_edit_route(report_id=response_object_id)

    @staticmethod
    @auth_required()
    def diff_view(report_id: str, from_rev: int, to_rev: int) -> tuple[str, int] | Response:
        """Display diff between two revisions"""
        if not report_id:
            return abort(400, description="No report ID provided.")

        # Get report data
        report = DataPersistenceLayer().get_object(ReportItem, report_id)
        if not report:
            return abort(404, description="Report not found.")

        # Get revision data from core API
        from_data = CoreApi().api_get(f"/analyze/report-items/{report_id}/revisions/{from_rev}")
        to_data = CoreApi().api_get(f"/analyze/report-items/{report_id}/revisions/{to_rev}")

        if not from_data or not to_data:
            return abort(404, description="Revision not found.")

        # Calculate diff
        from_revision_data = from_data.get("data", {})
        to_revision_data = to_data.get("data", {})

        # Prepare diff data
        diff_data = {
            "from_revision": from_data,
            "to_revision": to_data,
            "changes": _calculate_diff(from_revision_data, to_revision_data),
        }

        context = {
            "report": report,
            "diff": diff_data,
            "from_rev": from_rev,
            "to_rev": to_rev,
        }

        return render_template("analyze/report_diff.html", **context), 200


# TODO: Enhance diff calculation to handle more complex attribute types and nested structures, and to provide better formatting of changes in the UI.
def _calculate_diff(from_data: dict, to_data: dict) -> list[dict[str, Any]]:
    """Calculate differences between two report data dictionaries"""
    changes = []

    # Compare title
    if from_data.get("title") != to_data.get("title"):
        changes.append(
            {
                "field": "Title",
                "old_value": from_data.get("title"),
                "new_value": to_data.get("title"),
            }
        )

    # Compare completed status
    if from_data.get("completed") != to_data.get("completed"):
        changes.append(
            {
                "field": "Completed",
                "old_value": from_data.get("completed"),
                "new_value": to_data.get("completed"),
            }
        )

    # Build story ID to title mapping for resolving STORY attribute values
    story_map = {}
    for story in from_data.get("stories", []) + to_data.get("stories", []):
        if story.get("id"):
            story_map[story["id"]] = story.get("title", story["id"])

    # Compare attributes
    from_attrs = from_data.get("grouped_attributes", [])
    to_attrs = to_data.get("grouped_attributes", [])

    # Create flattened attribute dictionaries for comparison, with type info
    from_attr_dict = {}
    from_attr_types = {}
    for group in from_attrs:
        for attr in group.get("attributes", []):
            key = f"{group.get('title', '')}.{attr.get('title', '')}"
            from_attr_dict[key] = attr.get("value")
            from_attr_types[key] = attr.get("type")

    to_attr_dict = {}
    to_attr_types = {}
    for group in to_attrs:
        for attr in group.get("attributes", []):
            key = f"{group.get('title', '')}.{attr.get('title', '')}"
            to_attr_dict[key] = attr.get("value")
            to_attr_types[key] = attr.get("type")

    # Find changed and new attributes
    for key in sorted(set(from_attr_dict.keys()) | set(to_attr_dict.keys())):
        from_val = from_attr_dict.get(key)
        to_val = to_attr_dict.get(key)

        if from_val != to_val:
            # Resolve STORY attribute values to titles
            attr_type = from_attr_types.get(key) or to_attr_types.get(key)
            if attr_type == "STORY":
                from_display = story_map.get(from_val, from_val) if from_val else None
                to_display = story_map.get(to_val, to_val) if to_val else None
            else:
                from_display = from_val
                to_display = to_val

            changes.append(
                {
                    "field": key,
                    "old_value": from_display,
                    "new_value": to_display,
                }
            )

    # Compare stories
    from_story_ids = {s.get("id") for s in from_data.get("stories", [])}
    to_story_ids = {s.get("id") for s in to_data.get("stories", [])}

    added_stories = to_story_ids - from_story_ids
    removed_stories = from_story_ids - to_story_ids

    if added_stories:
        story_titles = [s.get("title", s.get("id")) for s in to_data.get("stories", []) if s.get("id") in added_stories]
        changes.append(
            {
                "field": "Stories Added",
                "old_value": None,
                "new_value": ", ".join(story_titles),
            }
        )

    if removed_stories:
        story_titles = [s.get("title", s.get("id")) for s in from_data.get("stories", []) if s.get("id") in removed_stories]
        changes.append(
            {
                "field": "Stories Removed",
                "old_value": ", ".join(story_titles),
                "new_value": None,
            }
        )

    return changes
