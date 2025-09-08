import base64
from typing import List, Dict, Optional, Union

from core.managers.data_manager import (
    get_template_content,
    list_templates,
)
from core.service.template_validation import validate_template_content


ContentType = Optional[Union[bytes, bytearray, memoryview, str]]


def _build_validation_and_content(content: ContentType):
    """Normalize content and compute validation_status and encoded content.

    Mirrors the inline logic previously in the API router to keep behavior identical.
    Returns a tuple: (encoded_content, validation_status), where encoded_content
    is a base64 string, "" (empty string), or None depending on input and errors.
    """
    if content is None:
        return None, {
            "is_valid": False,
            "error_message": "Template file not found.",
            "error_type": "NotFound",
        }
    if content == "__INVALID_UTF8__":
        return None, {
            "is_valid": False,
            "error_message": "Template file is not valid UTF-8.",
            "error_type": "UnicodeDecodeError",
        }
    if content == "__EMPTY__":
        return "", {
            "is_valid": False,
            "error_message": "Template file is empty.",
            "error_type": "EmptyFile",
        }

    # content is actual data; ensure we have a str for validation/encoding
    text: Optional[str]
    if isinstance(content, str):
        text = content
    elif isinstance(content, (bytes, bytearray, memoryview)):
        try:
            text = bytes(content).decode("utf-8")
        except Exception:
            return None, {
                "is_valid": False,
                "error_message": "Template file is not valid UTF-8.",
                "error_type": "UnicodeDecodeError",
            }
    else:
        # Unknown type; treat as not found/invalid
        return None, {
            "is_valid": False,
            "error_message": "Template file not found.",
            "error_type": "NotFound",
        }

    validation_status = validate_template_content(text)
    encoded_content = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    return encoded_content, validation_status


def build_template_response(template_path: str) -> Dict:
    """Return a dict with id, content (base64|None|""), and validation_status for a template."""
    content = get_template_content(template_path)
    encoded_content, validation_status = _build_validation_and_content(content)
    return {
        "id": template_path,
        "content": encoded_content,
        "validation_status": validation_status,
    }


def build_templates_list() -> List[Dict]:
    """Return a list of template dicts as provided by build_template_response for all templates."""
    items: List[Dict] = []
    for tid in list_templates():
        content = get_template_content(tid)
        encoded_content, validation_status = _build_validation_and_content(content)
        items.append({
            "id": tid,
            "content": encoded_content,
            "validation_status": validation_status,
        })
    return items
