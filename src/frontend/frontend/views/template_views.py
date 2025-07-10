from typing import Any
from base64 import b64decode, b64encode
from flask import request, render_template, Response

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
    def get_view_context(
        cls,
        objects: list | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Override to use enhanced templates with validation status."""
        # If we have objects and this is for the list view, enhance them with validation status first
        enhanced_objects = objects
        if objects:
            # Handle both paginated objects (with .data attribute) and simple lists
            template_list = objects.data if hasattr(objects, 'data') else objects
            if template_list and len(template_list) > 0:
                dpl = DataPersistenceLayer()
                try:
                    # Get validation status from API
                    api_result = dpl.api.api_get("/config/templates", params={"list": "true"})
                    if api_result and "items" in api_result:
                        # Create a mapping of template names to validation status
                        validation_map = {}
                        for item in api_result["items"]:
                            template_id = item.get("id")
                            if template_id:
                                validation_map[template_id] = {
                                    "validation_status": item.get("validation_status", {})
                                }
                        
                        # Create enhanced template objects that support dynamic attributes
                        enhanced_templates = []
                        for template_obj in template_list:
                            if hasattr(template_obj, 'id') and getattr(template_obj, 'id') in validation_map:
                                template_id = getattr(template_obj, 'id')
                                # Create a dict-like object that supports both attribute and dict access
                                enhanced_template = type('EnhancedTemplate', (), {
                                    'id': template_id,
                                    'content': getattr(template_obj, 'content', ''),
                                    'validation_status': validation_map[template_id]["validation_status"],
                                    '__getitem__': lambda self, key: getattr(self, key),
                                    '__contains__': lambda self, key: hasattr(self, key)
                                })()
                                
                                # Copy all other attributes from the original template
                                for attr in dir(template_obj):
                                    if not attr.startswith('_') and not hasattr(enhanced_template, attr):
                                        try:
                                            setattr(enhanced_template, attr, getattr(template_obj, attr))
                                        except Exception:
                                            pass
                                
                                enhanced_templates.append(enhanced_template)
                            else:
                                # For templates without validation data, just use the original
                                enhanced_templates.append(template_obj)
                        
                        # Update the appropriate container with enhanced templates
                        if hasattr(objects, 'data'):
                            objects.data = enhanced_templates
                            enhanced_objects = objects
                        else:
                            # For CacheObject or other list-like pagination objects, replace contents in place
                            objects.clear()
                            objects.extend(enhanced_templates)
                            enhanced_objects = objects
                
                except Exception as e:
                    logger.warning(f"Failed to enhance templates with validation status in get_view_context: {e}")
        
        # Now create the context with the enhanced objects
        context = super().get_view_context(enhanced_objects, error)
        
        # Ensure the template_data context variable contains our enhanced templates
        if enhanced_objects:
            context[cls.model_plural_name()] = enhanced_objects
        
        return context

    @classmethod
    def get_extra_context(cls, object_id: int | str) -> dict[str, Any]:
        # Just use the default behavior - validation status for list view is handled by get_view_context
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

        validation_status = None
        if object_id != 0 and str(object_id) != '0':  # Only for existing templates
            try:
                validation_response = dpl.api.api_get(f"/config/templates/{object_id}")
                if validation_response:
                    # Always assign content from API response, even if invalid
                    template.content = b64decode(validation_response.get("content", "") or "").decode("utf-8")
                    validation_status = validation_response.get("validation_status", {})
            except Exception as e:
                logger.warning(f"Failed to fetch validation status for template {object_id}: {e}")
        else:
            try:
                template.content = b64decode(template.content or "").decode("utf-8")
            except Exception:
                logger.exception()
                logger.warning(f"Failed to decode template content for {template}")
                template.content = template.content

        context[cls.model_name()] = template
        context["validation_status"] = validation_status
        return context

    @classmethod
    def process_form_data(cls, object_id: str | int):
        try:
            form_data = parse_formdata(request.form)
            obj = Template(**form_data)
            if obj.content:
                obj.content = b64encode(obj.content.encode("utf-8")).decode("utf-8")
            dpl = DataPersistenceLayer()
            result = dpl.store_object(obj) if object_id == 0 else dpl.update_object(obj, object_id)
            return (result.json(), None) if result.ok else (None, result.json().get("error"))
        except Exception as exc:
            logger.error(f"Error storing form data: {str(exc)}")
            return None, str(exc)

    @classmethod
    def update_view(cls, object_id: int | str = 0):
        resp_obj, error = cls.process_form_data(object_id)
        if resp_obj and not error:
            return Response(status=200, headers={"HX-Redirect": cls.get_base_route()})

        return render_template("notification/index.html", notification={"message": error, "error": True}), 400
