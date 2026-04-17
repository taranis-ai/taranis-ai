from models.base import TaranisBaseModel
from pydantic import ValidationError


def format_pydantic_errors(exc: ValidationError, model: type[TaranisBaseModel]) -> str:
    return model.format_validation_errors(exc)
