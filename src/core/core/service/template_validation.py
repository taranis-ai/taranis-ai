"""
Template validation logic for Taranis AI core.

This module provides Jinja2 template validation for the core API.
"""

from jinja2 import Environment, TemplateSyntaxError, DebugUndefined, UndefinedError


def validate_template_content(template_content: str) -> dict:
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
        return {
            "is_valid": False,
            "error_message": "Template file is empty.",
            "error_type": "EmptyFile"
        }

    try:
        # Create Jinja2 environment with DebugUndefined for better error messages
        env = Environment(autoescape=False, undefined=DebugUndefined)

        # Compile and attempt to render with empty context
        template = env.from_string(template_content)
        try:
            template.render({})
        except UndefinedError:
            # Ignore undefined variable errors - these are expected with empty context
            pass
        except Exception as e:
            # Catch other rendering errors (e.g., filter errors, logic errors)
            return {
                "is_valid": False,
                "error_message": str(e),
                "error_type": type(e).__name__
            }

        # Template is valid
        return {
            "is_valid": True,
            "error_message": "",
            "error_type": ""
        }

    except TemplateSyntaxError as e:
        return {
            "is_valid": False,
            "error_message": str(e),
            "error_type": "TemplateSyntaxError"
        }
    except Exception as e:
        return {
            "is_valid": False,
            "error_message": str(e),
            "error_type": type(e).__name__
        }
