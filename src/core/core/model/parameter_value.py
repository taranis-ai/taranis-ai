from typing import Any
from core.managers.log_manager import logger

from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.parameter import Parameter


class ParameterValue(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(), nullable=False, default="")

    parameter_key = db.Column(db.String(), db.ForeignKey("parameter.key"))
    parameter = db.relationship("Parameter")

    def __init__(self, value, parameter):
        self.id = None
        self.value = value
        self.parameter_key = parameter

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["parameter"] = Parameter.find_by_key(data.pop("parameter_key")).to_dict()
        return data

    def to_simple_dict(self) -> dict[str, Any]:
        return {self.parameter_key: self.value}

    @classmethod
    def find_param_value(cls, p_values: list["ParameterValue"], key: str) -> "ParameterValue":
        # Helper function to find parameter value based on key
        return next((pv for pv in p_values if pv.parameter.key == key), None)
