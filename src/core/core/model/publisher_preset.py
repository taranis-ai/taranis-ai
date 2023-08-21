from typing import Any
import uuid

from core.managers.log_manager import logger
from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.parameter_value import ParameterValue
from core.model.worker import PUBLISHER_TYPES, Worker


class PublisherPreset(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    publisher_type = db.Column(db.Enum(PUBLISHER_TYPES))
    parameter_values = db.relationship("ParameterValue", secondary="publisher_preset_parameter_value", cascade="all")

    def __init__(
        self,
        name,
        description,
        publisher_type,
        parameter_values=None,
        id=None,
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.publisher_type = publisher_type
        self.parameter_values = (
            ParameterValue.get_or_create_from_list(parameter_values) if parameter_values else Worker.get_parameters(publisher_type)
        )

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
    def get_all_for_publisher_json(cls, parameters):
        for publisher in cls.publisher.query.all():
            if publisher.type == parameters.publisher_type:
                return [preset.to_dict() for preset in publisher.sources]

    @classmethod
    def update(cls, preset_id, data):
        preset = cls.get(preset_id)
        if not preset:
            logger.error(f"Could not find preset with id {preset_id}")
            return None
        updated_preset = cls.from_dict(data)
        preset.name = updated_preset.name
        preset.description = updated_preset.description
        preset.parameter_values = updated_preset.parameter_values
        db.session.commit()
        return preset.id

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["parameter_values"] = {value.parameter: value.value for value in self.parameter_values}
        data["tag"] = "mdi-file-star-outline"
        return data


class PublisherPresetParameterValue(BaseModel):
    publisher_preset_id = db.Column(db.String, db.ForeignKey("publisher_preset.id"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
