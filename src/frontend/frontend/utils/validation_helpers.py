from typing import Any, Type

from models.base import TaranisBaseModel
from pydantic import ValidationError


def format_pydantic_errors(exc: ValidationError, model: Type[Any]) -> str:
    if isinstance(model, type) and issubclass(model, TaranisBaseModel) and hasattr(model, "format_validation_errors"):
        return model.format_validation_errors(exc)
    return f"Validation failed for model {getattr(model, '__name__', str(model))}, but no error details were extracted."
