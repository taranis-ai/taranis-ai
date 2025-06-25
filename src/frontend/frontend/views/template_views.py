from typing import Any
from base64 import b64decode, b64encode
from flask import request

from frontend.views.base_view import BaseView
from frontend.log import logger
from models.admin import Template
from frontend.data_persistence import DataPersistenceLayer
from frontend.utils.form_data_parser import parse_formdata


class TemplateView(BaseView):
    model = Template
    icon = "document-text"
    _index = 160

    @classmethod
    def model_plural_name(cls) -> str:
        return "template_data"

    @classmethod
    def get_columns(cls):
        from frontend.filters import render_validation_status
        return [
            {"title": "Template Name", "field": "id", "sortable": True, "renderer": None},
            {"title": "Validation Status", "field": "validation_status", "sortable": False, "renderer": render_validation_status}
        ]

    @classmethod
    def get_extra_context(cls, object_id: int | str) -> dict[str, Any]:
        """Override to fetch templates with validation status for the list view."""
        if object_id == 0 or str(object_id) == '0':  # List view case
            # For the list view, fetch templates with validation status
            dpl = DataPersistenceLayer()
            
            # Call the core API directly with list=true to get validation status
            api_result = dpl.api.api_get("/config/templates", params={"list": "true"})
            
            if api_result and "items" in api_result:
                # Convert API result to Template objects with validation status
                template_objects = []
                for item in api_result["items"]:
                    # Map the API response fields to Template model fields
                    template_data = {
                        "id": item.get("path"),  # Map path to id
                        "content": None,  # Content is not needed for list view
                        "validation_status": item.get("validation_status", {}),
                        "is_dirty": item.get("is_dirty", False)
                    }
                    template_obj = cls.model(**template_data)
                    template_objects.append(template_obj)
                
                # Override the cache for this request
                from frontend.cache import cache
                from frontend.cache_models import CacheObject
                cache_object = CacheObject(
                    template_objects,
                    total_count=api_result.get("total_count", len(template_objects)),
                    links=api_result.get("_links", {}),
                )
                cache_key = dpl.make_user_key(cls.model._core_endpoint)
                cache.set(key=cache_key, value=cache_object, timeout=cache_object.timeout)
        
        return super().get_extra_context(object_id)

    @classmethod
    def _get_object_key(cls) -> str:
        return f"{cls.model_name().lower()}"

    @classmethod
    def get_update_context(
        cls,
        object_id: int | str,
        error: str | None = None,
        form_error: str | None = None,
        resp_obj=None,
    ) -> dict[str, Any]:
        context = super().get_update_context(
            object_id=object_id,
            error=error,
            form_error=form_error,
            resp_obj=resp_obj,
        )

        dpl = DataPersistenceLayer()
        template: Template = dpl.get_object(cls.model, object_id) or cls.model.model_construct()  # type: ignore

        try:
            template.content = b64decode(template.content or "").decode("utf-8")
        except Exception:
            logger.exception()
            logger.warning(f"Failed to decode template content for {template}")
            template.content = template.content

        # Fetch template validation status for dirty flag display
        validation_status = None
        is_dirty = False
        if object_id != 0 and str(object_id) != '0':  # Only for existing templates
            try:
                # IMPROVED: Simple on-demand validation (no JSON file needed)
                validation_response = dpl.api.api_get(f"/config/templates/{object_id}")
                if validation_response:
                    # Template content is already available in validation_response
                    validation_status = validation_response.get("validation_status", {})
                    is_dirty = validation_response.get("is_dirty", False)
                    
                    # Alternative: Direct validation without JSON file dependency
                    # This would be even simpler but requires template content access
                    # template_content = template.content  # Already decoded above
                    # from jinja2 import Environment, TemplateSyntaxError
                    # try:
                    #     env = Environment(autoescape=False)
                    #     env.parse(template_content)
                    #     validation_status = {"is_valid": True, "error_message": "", "error_type": ""}
                    #     is_dirty = False
                    # except TemplateSyntaxError as e:
                    #     validation_status = {"is_valid": False, "error_message": str(e), "error_type": "TemplateSyntaxError"}
                    #     is_dirty = True
            except Exception as e:
                logger.warning(f"Failed to fetch validation status for template {object_id}: {e}")

        context[cls.model_name()] = template
        context["validation_status"] = validation_status
        context["is_dirty"] = is_dirty
        return context

    @classmethod
    def process_form_data(cls, object_id: str | int):
        try:
            if isinstance(object_id, int):
                object_id = f"{object_id}"
            obj = Template(id=object_id, **parse_formdata(request.form))
            if obj.content:
                obj.content = b64encode(obj.content.encode("utf-8")).decode("utf-8")
            dpl = DataPersistenceLayer()
            result = dpl.store_object(obj) if object_id == 0 else dpl.update_object(obj, object_id)
            return (result.json(), None) if result.ok else (None, result.json().get("error"))
        except Exception as exc:
            return None, str(exc)
