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
    htmx_list_template: str = "template/template_data_table.html"

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
        template_data = dpl.get_object(cls.model, object_id)
        
        # Handle both new templates (object_id == 0) and existing templates
        if object_id == 0 or str(object_id) == '0':
            # New template - create empty template object with proper defaults
            template = cls.model.model_construct(id='0', content='')
            validation_status = None
        elif template_data:
            # Existing template - handle both dict and Template object
            if isinstance(template_data, dict):
                # template_data is a dict from API (from cache or direct fetch)
                try:
                    # Decode base64 content for display
                    decoded_content = b64decode(template_data.get("content", "") or "").decode("utf-8")
                    template_data_with_decoded_content = template_data.copy()
                    template_data_with_decoded_content["content"] = decoded_content
                    
                    # Create a template object from the dict with decoded content
                    template = cls.model.model_construct(**template_data_with_decoded_content)
                except Exception as e:
                    logger.warning(f"Failed to decode template content for {object_id}: {e}")
                    # Create template with original content if decoding fails
                    template = cls.model.model_construct(**template_data)
                
                # Extract validation status from the dict
                validation_status = template_data.get("validation_status", {})
            else:
                # template_data is a Template object
                template = template_data
                
                # Decode base64 content for display if needed
                content = getattr(template, 'content', None)
                if content:
                    try:
                        # Try to decode base64 content
                        decoded_content = b64decode(content).decode("utf-8")
                        setattr(template, 'content', decoded_content)
                    except Exception as e:
                        logger.warning(f"Failed to decode template content for {object_id}: {e}")
                        # Keep original content if decoding fails
                
                # Extract validation status from the template object
                validation_status = getattr(template, 'validation_status', None) or {}
        else:
            # Fallback if template not found
            template = cls.model.model_construct()
            validation_status = None

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
