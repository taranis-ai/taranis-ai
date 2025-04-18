import json
from typing import Any
from enum import StrEnum, auto
from sqlalchemy.orm import Mapped

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.log import logger


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
    CRON_INTERVAL = auto()


class ParameterValue(BaseModel):
    __tablename__ = "parameter_value"

    id: Mapped[int] = db.Column(db.Integer, primary_key=True)
    parameter: Mapped[str] = db.Column(db.String, nullable=False)
    value: Mapped[str] = db.Column(db.String, nullable=False, default="")
    type: Mapped[PARAMETER_TYPES] = db.Column(db.Enum(PARAMETER_TYPES), nullable=False)
    rules: Mapped[str] = db.Column(db.String, nullable=True)

    def __init__(
        self, parameter: str, value: str = "", type: str | PARAMETER_TYPES = "text", rules: str | None | list = None, id: int | None = None
    ):
        self.parameter = parameter
        self.value = value
        self.type = type if isinstance(type, PARAMETER_TYPES) else PARAMETER_TYPES(type.lower())
        if rules:
            self.rules = ",".join(rules) if isinstance(rules, list) else rules
        if id:
            self.id = id

    def to_dict(self) -> dict[str, str]:
        return {self.parameter: self.value}

    def get_copy(self) -> "ParameterValue":
        return ParameterValue(parameter=self.parameter, value=self.value, type=self.type, rules=self.rules)

    @classmethod
    def find_value_by_parameter(cls, parameters: list["ParameterValue"], parameter_key: str) -> str:
        return next((parameter.value for parameter in parameters if parameter.parameter == parameter_key), "")

    @classmethod
    def find_by_parameter(cls, parameters: list["ParameterValue"], parameter_key: str) -> "ParameterValue | None":
        return next((parameter for parameter in parameters if parameter.parameter == parameter_key), None)

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
        base_parameters_dict = {parameter.parameter: parameter for parameter in base_parameters}

        for update_parameter in update_parameters:
            if update_parameter.parameter in base_parameters_dict:
                logger.debug(f"Updating: {update_parameter.parameter}")
                base_parameters_dict[update_parameter.parameter].value = update_parameter.value
            else:
                # Add new parameters from update_parameters that are not in base_parameters
                logger.debug(f"Adding new parameter: {update_parameter.parameter}")
                base_parameters.append(update_parameter)

        for parameter in base_parameters:
            parameter.check_rules()

        return base_parameters

    @classmethod
    def from_parameter_list(cls, parameters: list[str]) -> list["ParameterValue"]:
        return [cls(parameter=parameter) for parameter in parameters]

    def check_rules(self) -> bool:
        if not self.rules:
            return True
        for rule in self.rules.split(","):
            if rule == "required":
                if not self.value:
                    raise ValueError("This parameter is required")
            if rule == "tlp":
                if self.value not in ["red", "amber", "amber+strict", "green", "clear", None, ""]:
                    raise ValueError("Invalid TLP allowed values: red, amber, amber+strict, green, clear")
            if rule == "json":
                if self.value:
                    json_dict = json.loads(self.value)
                    if not isinstance(json_dict, dict):
                        raise ValueError('Input has to be a json of format \'{"<str>": "<str>"}\'')

        return True
