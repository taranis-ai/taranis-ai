from typing import Any

from flask import Response, abort, make_response, render_template, request, url_for
from flask.typing import ResponseReturnValue
from models.assess import Story
from models.report import ReportItem, ReportItemAttributeGroup, ReportTypes
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

    @classmethod
    def get_extra_context(cls, base_context: dict[str, Any]) -> dict[str, Any]:
        try:
            dpl = DataPersistenceLayer()
            report_types = dpl.get_objects(ReportTypes)
            base_context["report_types"] = report_types
            layout = request.args.get("layout") or request.form.get("layout") or base_context.get("layout", "split")
            report = base_context.get("report")
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

    @classmethod
    def delete_view(cls, object_id: str | int) -> tuple[str, int]:
        core_response = DataPersistenceLayer().delete_object(cls.model, object_id)

        response = cls.get_notification_from_response(core_response)
        table, table_response = cls.render_list()
        if table_response == 200:
            response += table
        return response, core_response.status_code or table_response

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
