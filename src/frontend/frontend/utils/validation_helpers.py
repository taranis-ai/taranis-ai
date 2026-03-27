from typing import Any, Type

from models.base import TaranisBaseModel
from pydantic import ValidationError


def extract_pydantic_errors(exc: ValidationError, model: Type[Any]) -> list[dict[str, str]]:
    if isinstance(model, type) and issubclass(model, TaranisBaseModel) and hasattr(model, "extract_validation_errors"):
        return model.extract_validation_errors(exc)

    return [
        {
            "model": getattr(model, "__name__", str(model)),
            "field": ".".join(str(loc) for loc in error["loc"]),
            "error": error["msg"],
            "error_type": error["type"],
        }
        for error in exc.errors()
    ]


def format_pydantic_errors(exc: ValidationError, model: Type[Any]) -> str:
    if isinstance(model, type) and issubclass(model, TaranisBaseModel) and hasattr(model, "format_validation_errors"):
        return model.format_validation_errors(exc)

    structured = extract_pydantic_errors(exc, model)
    if not structured:
        return f"Validation failed for model {getattr(model, '__name__', str(model))}, but no error details were extracted."

    lines = [f"Validation failed for model '{getattr(model, '__name__', str(model))}':"]
    lines.extend(f"  • Field '{err['field']}': {err['error']} (type={err['error_type']})" for err in structured)
    return "\n".join(lines)
