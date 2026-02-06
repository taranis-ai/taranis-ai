import base64

from core.managers.data_manager import save_template_content
from core.service.template_validation import validate_template_content


def create_or_update_template(template_id, base64_content):
    """
    Shared logic for creating or updating a template.
    Decodes base64 content, validates, and saves the template.
    Returns a tuple: (response_dict, status_code)
    """
    if not template_id or not base64_content:
        return {"error": "Missing template id or content"}, 400

    # Decode content
    try:
        template_content = base64.b64decode(base64_content).decode("utf-8")
    except Exception as e:
        return {"error": f"Failed to decode content: {e}"}, 400

    # Validate
    validation_status = validate_template_content(template_content)

    # Store in file
    try:
        save_template_content(template_id, template_content)
    except Exception as e:
        return {"error": f"Failed to save template: {e}"}, 500

    response = {"message": "Template updated or created", "path": template_id, "validation_status": validation_status}
    if not validation_status["is_valid"]:
        response["warning"] = f"Template saved but has validation errors: {validation_status['error_message']}"
    return response, 200
