from typing import Any
import uuid

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.parameter_value import ParameterValue
from core.model.worker import PUBLISHER_TYPES, Worker


class PublisherPreset(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    name: Any = db.Column(db.String(), nullable=False)
    description: Any = db.Column(db.String())
    type = db.Column(db.Enum(PUBLISHER_TYPES))
    parameters: Any = db.relationship("ParameterValue", secondary="publisher_preset_parameter_value", cascade="all, delete")

    def __init__(
        self,
        name,
        type,
        description=None,
        parameters=None,
        id=None,
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.parameters = Worker.parse_parameters(type, parameters)

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(PublisherPreset.name)).all()

    @classmethod
    def get_by_filter(cls, search=None):
        query = cls.query

        if search:
            query = query.filter(
                db.or_(
                    cls.name.ilike(f"%{search}%"),
                    cls.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(cls.name).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        publishers, count = cls.get_by_filter(search)
        items = [publisher.to_dict() for publisher in publishers]
        return {"total_count": count, "items": items}

    @classmethod
    def update(cls, preset_id, data):
        preset = cls.get(preset_id)
        if not preset:
            logger.error(f"Could not find preset with id {preset_id}")
            return {"error": f"Could not find preset with id {preset_id}"}, 404
        if name := data.get("name"):
            preset.name = name

        preset.description = data.get("description")

        if parameters := data.get("parameters"):
            updated_preset = ParameterValue.get_or_create_from_list(parameters)
            preset.parameters = ParameterValue.get_update_values(preset.parameters, updated_preset)
        db.session.commit()
        return {"message": "Successfully updated", "id": preset.id}, 200

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["parameters"] = {parameter.parameter: parameter.value for parameter in self.parameters}
        return data


class PublisherPresetParameterValue(BaseModel):
    publisher_preset_id = db.Column(db.String, db.ForeignKey("publisher_preset.id", ondelete="CASCADE"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
