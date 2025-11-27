from typing import Any
from flask import request, abort, Response, url_for, render_template
from pydantic import ValidationError

from frontend.log import logger
from models.assess import Story
from models.report import ReportItem, ReportItemAttributeGroup
from models.admin import ReportItemType
from frontend.views.base_view import BaseView
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_datetime, render_count
from frontend.auth import auth_required
from frontend.core_api import CoreApi
from frontend.utils.form_data_parser import parse_formdata
from frontend.utils.validation_helpers import format_pydantic_errors


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
            {"title": "Type", "field": "report_item_type", "sortable": True, "renderer": None},
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
        for ag in grouped_attributes:
            story_attributes.extend(a for a in ag.attributes if a.type and a.type == "STORY")
        return story_attributes

    @classmethod
    def get_extra_context(cls, base_context: dict[str, Any]) -> dict[str, Any]:
        report_types = DataPersistenceLayer().get_objects(ReportItemType)
        base_context["report_types"] = report_types
        layout = request.args.get("layout", base_context.get("layout", "split"))
        report = base_context.get("report")
        if report and report.grouped_attributes:
            base_context["story_attributes"] = ReportItemView._get_story_attributes(report.grouped_attributes) or []

        base_context |= {
            "layout": layout,
            "actions": cls.get_report_actions(),
        }

        return base_context

    @classmethod
    def get_create_context(cls) -> dict[str, Any]:
        context = super().get_create_context()
        report = context.get("report")
        if not report:
            return context
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
    def clone_report(report_id: str) -> tuple[str, int] | Response:
        if not report_id:
            return abort(400, description="No report ID provided for cloning.")
        CoreApi().clone_report(report_id)
        DataPersistenceLayer().invalidate_cache_by_object(ReportItem)
        return ReportItemView.list_view()

    def post(self, *args, **kwargs) -> tuple[str, int] | Response:
        return self.update_view(object_id=0)

    def put(self, **kwargs) -> tuple[str, int] | Response:
        object_id = self._get_object_id(kwargs)
        if object_id is None:
            return abort(405)
        return self.update_view(object_id=object_id)

    @staticmethod
    def _parse_form_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
        return {key: ",".join(value) if isinstance(value, list) else value for key, value in attributes.items()}

    @classmethod
    def process_form_data(cls, object_id: int | str):
        try:
            form_data = parse_formdata(request.form)
            logger.debug(f"Parsed form data: {form_data}")
            form_data["attributes"] = cls._parse_form_attributes(form_data.get("attributes", {}))
            return cls.store_form_data(form_data, object_id)
        except ValidationError as exc:
            logger.error(format_pydantic_errors(exc, cls.model))
            return None, format_pydantic_errors(exc, cls.model)
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


def _calculate_diff(from_data: dict, to_data: dict) -> list[dict[str, Any]]:
    """Calculate differences between two report data dictionaries"""
    changes = []
    
    # Compare title
    if from_data.get("title") != to_data.get("title"):
        changes.append({
            "field": "Title",
            "old_value": from_data.get("title"),
            "new_value": to_data.get("title"),
        })
    
    # Compare completed status
    if from_data.get("completed") != to_data.get("completed"):
        changes.append({
            "field": "Completed",
            "old_value": from_data.get("completed"),
            "new_value": to_data.get("completed"),
        })
    
    # Compare attributes
    from_attrs = from_data.get("grouped_attributes", [])
    to_attrs = to_data.get("grouped_attributes", [])
    
    # Create flattened attribute dictionaries for comparison
    from_attr_dict = {}
    for group in from_attrs:
        for attr in group.get("attributes", []):
            from_attr_dict[f"{group.get('title', '')}.{attr.get('title', '')}"] = attr.get("value")
    
    to_attr_dict = {}
    for group in to_attrs:
        for attr in group.get("attributes", []):
            to_attr_dict[f"{group.get('title', '')}.{attr.get('title', '')}"] = attr.get("value")
    
    # Find changed and new attributes
    for key in set(from_attr_dict.keys()) | set(to_attr_dict.keys()):
        from_val = from_attr_dict.get(key)
        to_val = to_attr_dict.get(key)
        if from_val != to_val:
            changes.append({
                "field": key,
                "old_value": from_val,
                "new_value": to_val,
            })
    
    # Compare stories
    from_story_ids = {s.get("id") for s in from_data.get("stories", [])}
    to_story_ids = {s.get("id") for s in to_data.get("stories", [])}
    
    added_stories = to_story_ids - from_story_ids
    removed_stories = from_story_ids - to_story_ids
    
    if added_stories:
        story_titles = [s.get("title", s.get("id")) for s in to_data.get("stories", []) if s.get("id") in added_stories]
        changes.append({
            "field": "Stories Added",
            "old_value": None,
            "new_value": ", ".join(story_titles),
        })
    
    if removed_stories:
        story_titles = [s.get("title", s.get("id")) for s in from_data.get("stories", []) if s.get("id") in removed_stories]
        changes.append({
            "field": "Stories Removed",
            "old_value": ", ".join(story_titles),
            "new_value": None,
        })
    
    return changes
