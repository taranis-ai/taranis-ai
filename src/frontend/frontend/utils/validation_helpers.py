from typing import Any

from models.base import TaranisBaseModel


def format_pydantic_errors(exc: Any, model: type[TaranisBaseModel]) -> str:
    return model.format_validation_errors(exc)
