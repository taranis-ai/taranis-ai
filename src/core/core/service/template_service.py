
import base64
import hashlib
from typing import List, Dict, Optional, Union, Tuple

from core.managers.data_manager import (
    get_template_content,
    list_templates,
)
from core.service.template_validation import validate_template_content

# Simple in-memory cache for template validation status
# Key: (template_path, content_hash) -> (encoded_content, validation_status)
_template_validation_cache: Dict[Tuple[str, str], Tuple[str, dict]] = {}

def _get_content_hash(content: Optional[str]) -> str:
    if content is None:
        return "__NONE__"
    if not isinstance(content, str):
        try:
            content = bytes(content).decode("utf-8")
        except Exception:
            return "__INVALID_UTF8__"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


ContentType = Optional[Union[bytes, bytearray, memoryview, str]]


def _build_validation_and_content(content: ContentType, template_path: Optional[str] = None):
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

    # Use cache if available
    cache_key = None
    if template_path is not None:
        content_hash = _get_content_hash(text)
        cache_key = (template_path, content_hash)
        if cache_key in _template_validation_cache:
            return _template_validation_cache[cache_key]

    validation_status = validate_template_content(text)
    encoded_content = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    if cache_key is not None:
        _template_validation_cache[cache_key] = (encoded_content, validation_status)
    return encoded_content, validation_status


def build_template_response(template_path: str) -> Dict:
    """Return a dict with id, content (base64|None|""), and validation_status for a template."""
    content = get_template_content(template_path)
    encoded_content, validation_status = _build_validation_and_content(content, template_path=template_path)
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
        encoded_content, validation_status = _build_validation_and_content(content, template_path=tid)
        items.append({
            "id": tid,
            "content": encoded_content,
            "validation_status": validation_status,
        })
    return items

# Invalidate cache for a template (call after update/delete)
def invalidate_template_validation_cache(template_path: str, content: Optional[str] = None):
    """Remove cached validation for a template. If content is given, only remove that hash; else remove all for path."""
    if content is not None:
        content_hash = _get_content_hash(content)
        _template_validation_cache.pop((template_path, content_hash), None)
    else:
        # Remove all cache entries for this template_path
        keys_to_remove = [k for k in _template_validation_cache if k[0] == template_path]
        for k in keys_to_remove:
            _template_validation_cache.pop(k, None)
