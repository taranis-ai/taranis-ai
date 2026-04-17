import base64
from typing import TypedDict

from jinja2 import DebugUndefined, TemplateSyntaxError, UndefinedError
from jinja2.sandbox import ImmutableSandboxedEnvironment

from core.managers.data_manager import (
    InvalidPresenterTemplatePathError,
    get_template_content,
    list_templates,
    save_template_content,
)


type TemplateContent = str | bytes | bytearray | memoryview | None


class ValidationStatus(TypedDict):
    is_valid: bool
    error_message: str
    error_type: str


class TemplateResponse(TypedDict):
    id: str
    content: str | None
    validation_status: ValidationStatus


_INVALID_UTF8_SENTINEL = "__INVALID_UTF8__"
_EMPTY_TEMPLATE_SENTINEL = "__EMPTY__"


def _error_status(message: str, error_type: str) -> ValidationStatus:
    return {
        "is_valid": False,
        "error_message": message,
        "error_type": error_type,
    }


def _decode_template_content(content: bytes | bytearray | memoryview) -> str | None:
    try:
        return bytes(content).decode("utf-8")
    except UnicodeDecodeError:
        return None


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
    except InvalidPresenterTemplatePathError as e:
        return {"error": str(e)}, 400
    except Exception as e:
        return {"error": f"Failed to save template: {e}"}, 500

    response = {
        "message": "Template updated or created",
        "path": template_id,
        "validation_status": validation_status,
    }
    if not validation_status["is_valid"]:
        response["warning"] = f"Template saved but has validation errors: {validation_status['error_message']}"
    return response, 200


def validate_template_content(template_content: str) -> ValidationStatus:
    """
    Validate Jinja2 template content with comprehensive validation.

    Performs both syntax parsing and render testing to catch template errors.
    Uses DebugUndefined to provide better error messages for undefined variables.

    Args:
        template_content (str): The template string to validate

    Returns:
        dict: {
            "is_valid": bool,
            "error_message": str,  # Empty string if valid
            "error_type": str      # Empty string if valid
        }
    """
    if not template_content or not template_content.strip():
        return {"is_valid": False, "error_message": "Template file is empty.", "error_type": "EmptyFile"}

    try:
        # Create Jinja2 environment with DebugUndefined for better error messages
        env = ImmutableSandboxedEnvironment(autoescape=False, undefined=DebugUndefined)

        # Compile and attempt to render with empty context
        template = env.from_string(template_content)
        try:
            template.render({})
        except UndefinedError:
            # Ignore undefined variable errors - these are expected with empty context
            pass
        except Exception as e:
            # Catch other rendering errors (e.g., filter errors, logic errors)
            return {"is_valid": False, "error_message": str(e), "error_type": type(e).__name__}

        # Template is valid
        return {"is_valid": True, "error_message": "", "error_type": ""}

    except TemplateSyntaxError as e:
        return {"is_valid": False, "error_message": str(e), "error_type": "TemplateSyntaxError"}
    except Exception as e:
        return {"is_valid": False, "error_message": str(e), "error_type": type(e).__name__}


def _build_validation_and_content(content: TemplateContent) -> tuple[str | None, ValidationStatus]:
    """Normalize template content and compute the API-ready payload fields."""
    if content is None:
        return None, _error_status("Template file not found.", "NotFound")

    if content == _INVALID_UTF8_SENTINEL:
        return None, _error_status("Template file is not valid UTF-8.", "UnicodeDecodeError")

    if content == _EMPTY_TEMPLATE_SENTINEL:
        return "", _error_status("Template file is empty.", "EmptyFile")

    if isinstance(content, str):
        text = content
    elif isinstance(content, bytes | bytearray | memoryview):
        if (text := _decode_template_content(content)) is None:
            return None, _error_status("Template file is not valid UTF-8.", "UnicodeDecodeError")
    else:
        return None, _error_status("Template file not found.", "NotFound")

    return base64.b64encode(text.encode("utf-8")).decode("utf-8"), validate_template_content(text)


def _build_template_response(template_id: str, content: TemplateContent) -> TemplateResponse:
    encoded_content, validation_status = _build_validation_and_content(content)
    return {
        "id": template_id,
        "content": encoded_content,
        "validation_status": validation_status,
    }


def build_template_response(template_path: str) -> TemplateResponse:
    """Return a template payload with id, base64 content, and validation status."""
    return _build_template_response(template_path, get_template_content(template_path))


def build_templates_list() -> list[TemplateResponse]:
    """Return API payloads for every stored presenter template."""
    return [_build_template_response(template_id, get_template_content(template_id)) for template_id in list_templates()]
