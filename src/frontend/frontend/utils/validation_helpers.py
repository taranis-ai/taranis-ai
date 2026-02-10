from typing import Any, Type

from pydantic import ValidationError


def extract_pydantic_errors(exc: ValidationError, model: Type[Any]) -> list[dict[str, str]]:
    """
    Extracts structured validation error info from a Pydantic ValidationError.
    """
    return [
        {
            "model": model.__name__,
            "field": ".".join(str(loc) for loc in error["loc"]),
            "error": error["msg"],
            "error_type": error["type"],
        }
        for error in exc.errors()
    ]


def format_pydantic_errors(exc: ValidationError, model: Type[Any]) -> str:
    """
    Formats the validation error info into a readable string.
    """
    structured = extract_pydantic_errors(exc, model)
    if not structured:
        return f"Validation failed for model {model.__name__}, but no error details were extracted."

    lines = [f"Validation failed for model '{model.__name__}':"]
    lines.extend(f"  • Field '{err['field']}': {err['error']} (type={err['error_type']})" for err in structured)
    return "\n".join(lines)
