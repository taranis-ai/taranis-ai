from typing import Any
from sqlalchemy import or_
import uuid

from core.managers.db_manager import db
from core.managers.log_manager import logger
from core.model.base_model import BaseModel
from core.model.parameter_value import ParameterValue


class Bot(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    type = db.Column(db.String(64), nullable=False)
    parameter_values = db.relationship("ParameterValue", secondary="bot_parameter_value", cascade="all")

    def __init__(self, name, description, type, parameter_values):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.parameter_values = parameter_values

    def to_bot_info_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            self.type: {parameter_value.parameter.key: parameter_value.value for parameter_value in self.parameter_values},
        }

    @classmethod
    def update(cls, bot_id, data) -> "Bot | None":
        bot = cls.get(bot_id)
        if not bot:
            return None

        try:
            bot.name = data.get("name", bot.name)
            bot.description = data.get("description", bot.description)

            cls.update_parameters(bot, data)

            db.session.commit()
            return bot
        except Exception:
            logger.log_debug_trace("Update Bot Parameters Failed")
            return None

    @classmethod
    def update_parameters(cls, bot, data):
        if p_values := data.get("parameter_values"):
            for updated_value in p_values:
                if pv := ParameterValue.find_param_value(bot.parameter_values, updated_value["parameter"]):
                    pv.value = updated_value["value"]
        elif bot_type_params := data.get(bot.type):
            for key, value in bot_type_params.items():
                if pv := ParameterValue.find_param_value(bot.parameter_values, key):
                    pv.value = value

    @classmethod
    def add(cls, data) -> tuple[str, int]:
        if cls.filter_by_type(data["type"]):
            return f"Bot with type {data['type']} already exists", 409
        bot = cls.from_dict(data)
        db.session.add(bot)
        db.session.commit()
        return f"Bot {bot.name} added", 201

    @classmethod
    def get_first(cls):
        return cls.query.first()

    @classmethod
    def filter_by_type(cls, type) -> "Bot | None":
        return cls.query.filter_by(type=type).first()

    @classmethod
    def get_all_by_type(cls, type):
        return cls.query.filter_by(type=type).all()

    @classmethod
    def get_by_filter(cls, search):
        query = cls.query

        if search:
            query = query.filter(
                or_(
                    Bot.name.ilike(f"%{search}%"),
                    Bot.description.ilike(f"%{search}%"),
                )
            )

        return query.order_by(db.asc(Bot.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        bots, count = cls.get_by_filter(search)
        items = [bot.to_bot_info_dict() for bot in bots]
        return {"total_count": count, "items": items}

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["parameter_values"] = [pv.to_dict() for pv in self.parameter_values]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Bot":
        if parameter_values := data.pop("parameter_values", None):
            data["parameter_values"] = [ParameterValue(**pv) for pv in parameter_values]

        return cls(**data)


class BotParameterValue(BaseModel):
    bot_id = db.Column(db.String, db.ForeignKey("bot.id"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
