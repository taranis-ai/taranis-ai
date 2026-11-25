import base64
import binascii
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, TypedDict

from jinja2 import DebugUndefined, StrictUndefined, TemplateSyntaxError, UndefinedError
from jinja2.sandbox import ImmutableSandboxedEnvironment
from pydantic import BaseModel

from core.log import logger
from core.managers.data_manager import (
    InvalidPresenterTemplatePathError,
    get_template_content,
    list_templates,
    save_template_content,
)
from core.model.product_type import ProductType
from core.model.report_item import ReportItem, ReportItemAttribute
from core.model.report_item_type import ReportItemType
from core.service.worker_parameters import effective_parameters


type TemplateContent = str | bytes | bytearray | memoryview | None

TEMPLATE_SYNTAX_ERROR_WARNING = "The template has a syntax error."
TEMPLATE_UNREADABLE_WARNING = "The template file could not be read."
TEMPLATE_CHECK_FAILED_WARNING = "Template compatibility could not be checked."


class ValidationStatus(TypedDict):
    is_valid: bool
    error_message: str
    error_type: str


class TemplateResponse(BaseModel):
    name: str
    content: str | None
    validation_status: ValidationStatus


def create_or_update_template(template_name, base64_content):
    """
    Shared logic for creating or updating a template.
    Decodes base64 content, validates, and saves the template.
    Returns a tuple: (response_dict, status_code)
    """
    if not template_name or not base64_content:
        return {"error": "Missing template name or content"}, 400

    # Decode content
    try:
        template_content = base64.b64decode(base64_content, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as e:
        logger.error("Failed to decode template content: %s", e)
        return {"error": "Failed to decode content"}, 400

    # Validate
    validation_status = validate_template_content(template_content)

    # Store in file
    try:
        save_template_content(template_name, template_content)
    except InvalidPresenterTemplatePathError:
        return {"error": "Invalid presenter template path"}, 400
    except OSError:
        logger.exception("Failed to save template %s", template_name)
        return {"error": "Failed to save template"}, 500

    response = {
        "message": "Template updated or created",
        "path": template_name,
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
        except Exception:
            # Catch other rendering errors (e.g., filter errors, logic errors)
            logger.exception("Template render validation failed")
            return {"is_valid": False, "error_message": "Template render validation failed.", "error_type": "TemplateRenderError"}

        # Template is valid
        return {"is_valid": True, "error_message": "", "error_type": ""}

    except TemplateSyntaxError:
        return {
            "is_valid": False,
            "error_message": "Expected an expression in template syntax.",
            "error_type": "TemplateSyntaxError",
        }
    except Exception:
        logger.exception("Template validation failed")
        return {"is_valid": False, "error_message": "Template validation failed.", "error_type": "TemplateValidationError"}


def _build_validation_and_content(content: TemplateContent) -> tuple[str | None, ValidationStatus]:
    """Normalize template content and compute the API-ready payload fields."""
    if content is None:
        return None, {"is_valid": False, "error_message": "Template file not found.", "error_type": "NotFound"}

    if isinstance(content, str):
        text = content
    elif isinstance(content, (bytes, bytearray, memoryview)):
        try:
            text = bytes(content).decode("utf-8")
        except UnicodeDecodeError:
            return None, {"is_valid": False, "error_message": "Template file is not valid UTF-8.", "error_type": "UnicodeDecodeError"}
    else:
        return None, {"is_valid": False, "error_message": "Template file not found.", "error_type": "NotFound"}

    if not text.strip():
        return "", {"is_valid": False, "error_message": "Template file is empty.", "error_type": "EmptyFile"}

    return base64.b64encode(text.encode("utf-8")).decode("utf-8"), validate_template_content(text)


def _build_template_response(template_name: str, content: TemplateContent) -> TemplateResponse:
    encoded_content, validation_status = _build_validation_and_content(content)
    return TemplateResponse(name=template_name, content=encoded_content, validation_status=validation_status)


def build_template_response(template_path: str) -> TemplateResponse:
    """Return a template payload with name, base64 content, and validation status."""
    return _build_template_response(template_path, get_template_content(template_path))


def build_templates_list(order: str | None = None) -> list[TemplateResponse]:
    """Return API payloads for every stored presenter template."""
    items = [_build_template_response(template_name, get_template_content(template_name)) for template_name in list_templates()]
    if order in {"name_asc", "name_desc"}:
        items.sort(key=lambda item: item.name.casefold(), reverse=order == "name_desc")
    return items


def product_type_compatibility_warnings(product_type: ProductType) -> list[str]:
    """Warn about report types the configured template cannot render. Never raises; saving stays allowed."""
    if not (template_path := product_type._get_template_path()):
        return []
    try:
        template_content = get_template_content(template_path)
        if not isinstance(template_content, str):
            return [TEMPLATE_UNREADABLE_WARNING]
        product = {
            "type": str(product_type.type),
            "type_id": product_type.id,
            "mime_type": product_type.get_mimetype(),
            "parameters": effective_parameters(product_type.type, product_type.parameters),
        }
        return check_template_compatibility(template_content, product_type.report_types, product)
    except Exception:
        logger.exception("Template compatibility check failed for product type %s", product_type.id)
        return [TEMPLATE_CHECK_FAILED_WARNING]


def check_template_compatibility(
    template_content: str,
    report_types: Iterable[ReportItemType],
    product: dict[str, Any] | None = None,
) -> list[str]:
    """Render the template like the presenter worker once per report type and return curated warnings.

    Each render uses a sample product with one empty report of that type, shaped like `Product.to_worker_dict()`.
    `product` overrides product-level sample values such as `parameters`. Never raises.
    """
    env = ImmutableSandboxedEnvironment(
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        newline_sequence="\n",
        undefined=StrictUndefined,
    )
    try:
        template = env.from_string(template_content)
    except TemplateSyntaxError:
        logger.info("Template compatibility check found a syntax error", exc_info=True)
        return [TEMPLATE_SYNTAX_ERROR_WARNING]
    except Exception:
        logger.exception("Template compatibility check could not compile the template")
        return [TEMPLATE_CHECK_FAILED_WARNING]

    warnings = []
    for report_type in report_types:
        try:
            template.render(data=_sample_product(report_type, product))
        except UndefinedError as exc:
            # The message may contain values computed by the template, so it stays in the log only.
            logger.info("Template is incompatible with report type %s: %s", report_type.title, exc)
            warnings.append(f"The template uses a value that is not available for report type '{report_type.title}'.")
        except Exception:
            logger.exception("Template could not be rendered with report type %s", report_type.title)
            warnings.append(f"The template could not be rendered for report type '{report_type.title}'.")
    return warnings


def _sample_product(report_type: ReportItemType, product: dict[str, Any] | None) -> dict[str, Any]:
    # Keys of Product.to_worker_dict() plus current_date, which the presenter worker adds.
    return {
        "id": "00000000-0000-0000-0000-000000000000",
        "title": "Sample product",
        "description": "",
        "type": "",
        "type_id": "",
        "mime_type": "",
        "parameters": {},
        "render_revision": "",
        **(product or {}),
        "report_items": [_sample_report_item(report_type)],
        "current_date": datetime.now(UTC).strftime("%Y-%m-%d"),
    }


def _sample_report_item(report_type: ReportItemType) -> dict[str, Any]:
    # Never added to the session; only used for the exact keys and shapes of ReportItem.to_product_dict().
    report_item = ReportItem(
        title="Sample report",
        report_item_type_id=report_type.id,
        attributes=[
            ReportItemAttribute(title=item.title, group_title=group.title)
            for group in report_type.attribute_groups
            for item in group.attribute_group_items
        ],
    )
    report_item.created = report_item.last_updated = ReportItem.utcnow()
    return report_item.to_product_dict()
