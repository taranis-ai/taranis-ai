from typing import ClassVar, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError


T = TypeVar("T", bound="TaranisBaseModel")


class TaranisBaseModel(BaseModel):
    _core_endpoint: ClassVar[str]
    _cache_timeout: ClassVar[int]
    _model_name: ClassVar[str] = ""
    _pretty_name: ClassVar[str] = ""

    model_config = ConfigDict(extra="allow")

    @classmethod
    def extract_validation_errors(cls, exc: ValidationError) -> list[dict[str, str]]:
        return [
            {
                "model": cls.__name__,
                "field": ".".join(str(loc) for loc in error["loc"]),
                "error": error["msg"],
                "error_type": error["type"],
            }
            for error in exc.errors()
        ]

    @classmethod
    def format_validation_errors(cls, exc: ValidationError) -> str:
        structured = cls.extract_validation_errors(exc)
        if not structured:
            return f"Validation failed for model {cls.__name__}, but no error details were extracted."

        lines = [f"Validation failed for model '{cls.__name__}':"]
        lines.extend(f"  • Field '{err['field']}': {err['error']} (type={err['error_type']})" for err in structured)
        return "\n".join(lines)

    @classmethod
    def validation_error_response(cls, exc: ValidationError, prefix: str) -> dict[str, str]:
        errors = "; ".join(f"{err['field']}: {err['error']}" for err in cls.extract_validation_errors(exc))
        return {"error": f"{prefix}{f': {errors}' if errors else ''}"}

    def model_dump(self, *args, **kwargs):
        kwargs.setdefault("exclude_none", True)
        kwargs.setdefault("exclude_defaults", False)
        kwargs.setdefault("exclude_unset", False)
        return super().model_dump(*args, **kwargs)
