from typing import Any

from models.types import PUBLISHER_TYPES
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql.expression import Select

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel
from core.model.parameter_value import ParameterValue
from core.model.worker import Worker


class PublisherPreset(BaseModel):
    __tablename__ = "publisher_preset"
    DEFAULT_TARANIS_ID = "00000000-0000-4000-8000-000000000001"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())
    type: Mapped[PUBLISHER_TYPES] = db.Column(db.Enum(PUBLISHER_TYPES))
    parameters: Mapped[list["ParameterValue"]] = relationship(
        "ParameterValue", secondary="publisher_preset_parameter_value", cascade="all, delete"
    )

    def __init__(
        self,
        name: str,
        type: PUBLISHER_TYPES,
        description: str = "",
        parameters=None,
        id: str | None = None,
    ):
        self.id = self.normalize_uuid_id(id)
        self.name = name
        self.description = description
        self.type = type
        self.parameters = Worker.parse_parameters(type, parameters)

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.where(
                db.or_(
                    cls.name.ilike(f"%{search}%"),
                    cls.description.ilike(f"%{search}%"),
                )
            )

        return query

    @classmethod
    def default_sort_column(cls) -> str:
        return "name_asc"

    @classmethod
    def update(cls, preset_id, data):
        preset = cls.get(preset_id)
        if not preset:
            logger.error(f"Could not find preset with id {preset_id}")
            return {"error": "Preset not found"}, 404
        if name := data.get("name"):
            preset.name = name

        preset.description = data.get("description")

        if parameters := data.get("parameters"):
            updated_preset = ParameterValue.get_or_create_from_list(parameters)
            preset.parameters = ParameterValue.get_update_values(preset.parameters, updated_preset)
        db.session.commit()
        return {"message": "Successfully updated", "id": preset.id}, 200

    @classmethod
    def ensure_default_taranis(cls) -> "PublisherPreset":
        if preset := cls.get(cls.DEFAULT_TARANIS_ID):
            return preset
        try:
            return cls.add(
                {
                    "id": cls.DEFAULT_TARANIS_ID,
                    "name": "Taranis Publisher",
                    "description": "Publisher for making products publicly available in Taranis",
                    "type": PUBLISHER_TYPES.TARANIS_PUBLISHER,
                }
            )
        except IntegrityError:
            db.session.rollback()
            if preset := cls.get(cls.DEFAULT_TARANIS_ID):
                return preset
            raise

    @classmethod
    def delete(cls, preset_id: str) -> tuple[dict[str, Any], int]:
        if preset_id == cls.DEFAULT_TARANIS_ID:
            return {"error": "The default Taranis publisher cannot be deleted"}, 400
        return super().delete(preset_id)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["parameters"] = {parameter.parameter: parameter.value for parameter in self.parameters}
        return data

    def to_user_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type.value if self.type else None,
        }

    @classmethod
    def get_for_publish_api(cls, preset_id: str) -> tuple[dict[str, Any], int]:
        if preset := cls.get(preset_id):
            return preset.to_user_dict(), 200
        return {"error": f"{cls.__name__} not found"}, 404

    @classmethod
    def get_all_for_publish_api(cls, filter_args: dict[str, Any] | None) -> tuple[dict[str, Any], int]:
        filter_args = filter_args or {}
        logger.debug(f"Filtering {cls.__name__} for publish API with {filter_args}")

        base_query = cls.get_filter_query(filter_args)
        query = base_query
        if not cls._should_fetch_all(filter_args):
            query = cls._add_paging_to_query(filter_args, query)

        query = cls._add_sorting_to_query(filter_args, query)
        items = cls.get_filtered(query) or []
        count = cls.get_filtered_count(base_query)
        return {"total_count": count, "items": [item.to_user_dict() for item in items]}, 200


class PublisherPresetParameterValue(BaseModel):
    publisher_preset_id = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("publisher_preset.id", ondelete="CASCADE"), primary_key=True)
    parameter_value_id = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("parameter_value.id"), primary_key=True)
