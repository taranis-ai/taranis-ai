import uuid
from datetime import datetime
from typing import Any, Type

from models.types import COLLECTOR_TYPES, CONNECTOR_TYPES
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, deferred, relationship

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.news_item import NewsItem
from core.model.parameter_value import ParameterValue
from core.model.story import Story
from core.model.worker import Worker


class Connector(BaseModel):
    __tablename__ = "connector"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())

    type: Mapped[CONNECTOR_TYPES] = db.Column(db.Enum(CONNECTOR_TYPES))
    parameters: Mapped[list["ParameterValue"]] = relationship("ParameterValue", secondary="connector_parameter_value", cascade="all, delete")
    icon: Any = deferred(db.Column(db.LargeBinary))
    state: Mapped[int] = db.Column(db.SmallInteger, default=-1)
    last_collected: Mapped[datetime] = db.Column(db.DateTime, default=None)
    last_attempted: Mapped[datetime] = db.Column(db.DateTime, default=None)
    last_error_message: Mapped[str | None] = db.Column(db.String, default=None, nullable=True)

    def __init__(self, name: str, description: str, type: str | COLLECTOR_TYPES, parameters=None, icon=None, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type if isinstance(type, CONNECTOR_TYPES) else CONNECTOR_TYPES(type.lower())
        if icon is not None and (icon_data := self.is_valid_base64(icon)):
            self.icon = icon_data

        self.parameters = Worker.parse_parameters(type, parameters)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["parameters"] = {parameter.parameter: parameter.value for parameter in self.parameters}
        return data

    @classmethod
    def add(cls, data):
        connector = cls.from_dict(data)
        db.session.add(connector)
        db.session.commit()
        connector.schedule_connector()
        return connector

    def schedule_connector(self):
        """TODO: Lower priority"""
        pass

    def unschedule_connector(self):
        """TODO: Lower priority"""
        pass

    @classmethod
    def update(cls, connector_id: str, data: dict) -> "Connector | None":
        connector = cls.get(connector_id)
        if not connector:
            return None
        if name := data.get("name"):
            connector.name = name
        connector.description = data.get("description", "")
        icon_str = data.get("icon")
        if icon_str is not None and (icon := connector.is_valid_base64(icon_str)):
            connector.icon = icon
        if parameters := data.get("parameters"):
            update_parameter = ParameterValue.get_or_create_from_list(parameters)
            connector.parameters = ParameterValue.get_update_values(connector.parameters, update_parameter)
        db.session.commit()
        connector.schedule_connector()
        return connector

    @classmethod
    def delete(cls, connector_id: str, force: bool = False) -> tuple[dict, int]:
        if not (connector := cls.get(connector_id)):
            return {"error": f"Connector with ID: {connector_id} not found"}, 404

        try:
            connector.unschedule_connector()
            db.session.delete(connector)
            db.session.commit()
            return {"message": f"Connecotor {connector.name} deleted", "id": f"{connector_id}"}, 200
        except IntegrityError as e:
            logger.warning(f"IntegrityError: {e.orig}")
            return {"error": f"Deleting Connector with ID: {connector_id} failed {str(e)}"}, 500

    @staticmethod
    def _update_last_change(model_class: Type, data: dict[str, str]) -> tuple[dict[str, str], int]:
        if not data:
            return {"error": "No data provided"}, 400

        for object_id, target_value in data.items():
            if target_value not in ["internal", "external"]:
                return {"error": f"Invalid value {target_value} for ID {object_id}, must be 'internal' or 'external'"}, 400

            if instance := model_class.get(object_id):
                instance.last_change = target_value
                logger.debug(f"Updated last_change for {model_class.__name__} with ID {object_id} to {target_value}")

        db.session.commit()
        return {"message": "Last change status updated for"}, 200

    @staticmethod
    def update_news_item_last_change(data: dict[str, str]):
        return Connector._update_last_change(NewsItem, data)

    @staticmethod
    def update_story_last_change(data: dict[str, str]):
        return Connector._update_last_change(Story, data)


class ConnectorParameterValue(BaseModel):
    connector_id: Mapped[str] = db.Column(db.String, db.ForeignKey("connector.id", ondelete="CASCADE"), primary_key=True)
    parameter_value_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("parameter_value.id", ondelete="CASCADE"), primary_key=True)
