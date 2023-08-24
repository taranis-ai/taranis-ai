from typing import Any
from core.managers.log_manager import logger
from enum import StrEnum, auto

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
    id: Any = db.Column(db.Integer, primary_key=True)
    parameter: Any = db.Column(db.String, nullable=False)
    value: Any = db.Column(db.String, nullable=False, default="")
    type: Any = db.Column(db.Enum(PARAMETER_TYPES), nullable=False, default="text")

    def __init__(self, parameter, value="", type="text", id=None):
        self.id = id
        self.parameter = parameter
        self.value = value
        self.type = type

    def to_dict(self) -> dict[int, Any]:
        return {self.parameter: self.value}

    def get_copy(self) -> "ParameterValue":
        return ParameterValue(self.parameter, self.value, self.type)

    def get_value_by_parameter(self, parameter: str) -> str | None:
        return self.value if self.parameter == parameter else None

    @classmethod
    def find_value_by_parameter(cls, parameters: list["ParameterValue"], parameter: str) -> str | None:
        for param in parameters:
            return param.get_value_by_parameter(parameter)
        return None

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
            if parameter.parameter in update_parameters:
                parameter.value = cls.find_value_by_parameter(update_parameters, parameter.parameter)
        return base_parameters

    @classmethod
    def from_parameter_list(cls, parameters: list[str]) -> list["ParameterValue"]:
        return [cls(parameter=parameter) for parameter in parameters]
