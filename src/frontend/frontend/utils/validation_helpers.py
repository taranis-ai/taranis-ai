from typing import Any

from models.base import TaranisBaseModel
from pydantic import ValidationError


def _extract_generic_validation_errors(exc: ValidationError, model: type[Any] | Any) -> list[dict[str, str]]:
    return [
        {
            "model": getattr(model, "__name__", str(model)),
            "field": ".".join(str(loc) for loc in error["loc"]),
            "error": error["msg"],
            "error_type": error["type"],
        }
        for error in exc.errors()
    ]


def format_pydantic_errors(exc: ValidationError, model: type[Any] | Any) -> str:
    if isinstance(model, type) and issubclass(model, TaranisBaseModel):
        return model.format_validation_errors(exc)

    structured = _extract_generic_validation_errors(exc, model)
    if not structured:
        return f"Validation failed for model {getattr(model, '__name__', str(model))}, but no error details were extracted."

    lines = [f"Validation failed for model '{getattr(model, '__name__', str(model))}':"]
    lines.extend(f"  • Field '{err['field']}': {err['error']} (type={err['error_type']})" for err in structured)
    return "\n".join(lines)
