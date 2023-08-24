from typing import Any
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import joinedload
import uuid

from core.managers.db_manager import db
from core.managers.log_manager import logger
from core.model.base_model import BaseModel
from core.model.parameter_value import ParameterValue
from core.model.worker import BOT_TYPES, Worker


class Bot(BaseModel):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    type = db.Column(db.Enum(BOT_TYPES))
    index = db.Column(db.Integer, unique=True, nullable=False)
    parameters = db.relationship("ParameterValue", secondary="bot_parameter_value", cascade="all, delete")

    def __init__(self, name, type, description=None, parameters=None, id=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type
        self.index = Bot.get_highest_index() + 1
        self.parameters = Worker.parse_parameters(type, parameters)

    @classmethod
    def update(cls, bot_id, data) -> "Bot | None":
        bot = cls.get(bot_id)
        if not bot:
            return None

        try:
            if name := data.get("name"):
                bot.name = name
            if description := data.get("description"):
                bot.description = description
            if parameters := data.get("parameters"):
                update_parameter = ParameterValue.get_or_create_from_list(parameters)
                bot.parameters = ParameterValue.get_update_values(bot.parameters, update_parameter)
            if index := data.get("index"):
                bot.index = bot.index if Bot.index_exists(index) else index
            db.session.commit()
            return bot
        except Exception:
            logger.log_debug_trace("Update Bot Parameters Failed")
            return None

    @classmethod
    def get_highest_index(cls):
        result = db.session.query(func.max(cls.index)).scalar()
        return result or 0

    @classmethod
    def index_exists(cls, index):
        return cls.query.filter_by(index=index).count() > 0

    @classmethod
    def add(cls, data) -> tuple[dict, int]:
        bot = cls.from_dict(data)
        db.session.add(bot)
        db.session.commit()
        return {"message": f"Bot {bot.name} added", "id": f"{bot.id}"}, 201

    @classmethod
    def get_first(cls):
        return cls.query.first()

    @classmethod
    def filter_by_type(cls, type: str) -> "Bot | None":
        filter_type = type.lower()
        if filter_type not in [types.value for types in BOT_TYPES]:
            return None
        return cls.query.filter_by(type=filter_type).first()

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
                    Bot.description.ilike(f"%{search}%"),  # type: ignore
                )
            )

        return query.order_by(db.asc(Bot.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search):
        bots, count = cls.get_by_filter(search)
        items = [bot.to_dict() for bot in bots]
        return {"total_count": count, "items": items}

    @classmethod
    def get_post_collection(cls):
        # This should return all bots where the parameter with the KEY RUN_AFTER_COLLECTOR has the value True
        bots = (
            cls.query.join(BotParameterValue, Bot.id == BotParameterValue.bot_id)
            .join(ParameterValue, BotParameterValue.parameter_value_id == ParameterValue.id)
            .filter(and_(ParameterValue.parameter == "RUN_AFTER_COLLECTOR", ParameterValue.value == "true"))
            .options(joinedload(Bot.parameters))
            .order_by(Bot.index)
            .all()
        )

        return [bot.to_dict() for bot in bots]

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["parameters"] = {parameter.parameter: parameter.value for parameter in self.parameters}
        return data


class BotParameterValue(BaseModel):
    bot_id = db.Column(db.String, db.ForeignKey("bot.id", ondelete="CASCADE"), primary_key=True)
    parameter_value_id = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
