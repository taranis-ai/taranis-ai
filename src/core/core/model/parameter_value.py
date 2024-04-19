from typing import Any
from enum import StrEnum, auto
from sqlalchemy.orm import Mapped

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class PARAMETER_TYPES(StrEnum):
    TEXT = auto()
    TEXTAREA = auto()
    NUMBER = auto()
    SWITCH = auto()
    CHECKBOX = auto()
    SELECT = auto()
    LIST = auto()
    DATE = auto()
    TABLE = auto()


class ParameterValue(BaseModel):
    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    parameter: Mapped[str] = db.Column(db.String, nullable=False)
    value: Mapped[str] = db.Column(db.String, nullable=False, default="")
    type: Mapped[PARAMETER_TYPES] = db.Column(db.Enum(PARAMETER_TYPES), nullable=False)
    rules: Mapped[str] = db.Column(db.String, nullable=True)

    def __init__(
        self, parameter: str, value: str = "", type: str | PARAMETER_TYPES = "text", rules: str | None = None, id: int | None = None
    ):
        self.id = id
        self.parameter = parameter
        self.value = value
        self.type = type if isinstance(type, PARAMETER_TYPES) else PARAMETER_TYPES(type.lower())
        self.rules = rules

    def to_dict(self) -> dict[str, str]:
        return {self.parameter: self.value}

    def get_copy(self) -> "ParameterValue":
        return ParameterValue(self.parameter, self.value, self.type)

    @classmethod
    def find_value_by_parameter(cls, parameters: list["ParameterValue"], parameter_key: str) -> str:
        return next((parameter.value for parameter in parameters if parameter.parameter == parameter_key), "")

    @classmethod
    def get_or_create(cls, data: dict[str, Any]) -> "ParameterValue":
        if "parameter" in data:
            return cls.from_dict(data)
        return cls.from_dict({"parameter": list(data.keys())[0], "value": list(data.values())[0]})

    @classmethod
    def get_or_create_from_list(cls, parameters: dict[str, Any] | list[str] | list[dict[str, Any]]) -> list["ParameterValue"]:
        if parameters and isinstance(parameters, list):
            if isinstance(parameters[0], dict):
                return [cls.get_or_create(parameter) for parameter in parameters]  # type: ignore
            return cls.from_parameter_list(parameters)  # type: ignore
        return [cls.get_or_create({"parameter": key, "value": val}) for key, val in parameters.items()]  # type: ignore

    @classmethod
    def get_update_values(cls, base_parameters: list["ParameterValue"], update_parameters: list["ParameterValue"]) -> list["ParameterValue"]:
        for parameter in base_parameters:
            if parameter.parameter in [parameter.parameter for parameter in update_parameters]:
                parameter.value = cls.find_value_by_parameter(update_parameters, parameter.parameter)
        return base_parameters

    @classmethod
    def from_parameter_list(cls, parameters: list[str]) -> list["ParameterValue"]:
        return [cls(parameter=parameter) for parameter in parameters]
