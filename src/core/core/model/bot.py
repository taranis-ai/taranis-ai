import uuid
from typing import Any, Sequence

from sqlalchemy import func
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import Select

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.parameter_value import ParameterValue
from core.model.worker import BOT_TYPES, Worker
from core.model.queue import ScheduleEntry


class Bot(BaseModel):
    __tablename__ = "bot"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())
    type: Mapped[BOT_TYPES] = db.Column(db.Enum(BOT_TYPES))
    index: Mapped[int] = db.Column(db.Integer, unique=True, nullable=False)
    parameters: Mapped[list[ParameterValue]] = relationship("ParameterValue", secondary="bot_parameter_value", cascade="all, delete")

    def __init__(self, name: str, type: str | BOT_TYPES, description: str = "", parameters=None, id: str | None = None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type if isinstance(type, BOT_TYPES) else BOT_TYPES(type.lower())
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

            bot.description = data.get("description")
            if parameters := data.get("parameters"):
                update_parameter = ParameterValue.get_or_create_from_list(parameters)
                bot.parameters = ParameterValue.get_update_values(bot.parameters, update_parameter)
            if index := data.get("index"):
                if not Bot.index_exists(index):
                    bot.index = index
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
        return db.select(cls).where(index=index).scalar()

    @classmethod
    def filter_by_type(cls, filter_type: str) -> "Bot | None":
        if filter_type.lower() not in [types.value for types in BOT_TYPES]:
            return None
        return db.session.execute(db.select(cls).where(cls.type == filter_type.lower())).scalar_one_or_none()

    @classmethod
    def get_all_by_type(cls, filter_type: str):
        return cls.get_filtered(db.select(cls).where(cls.type == filter_type))

    @classmethod
    def get_post_collection(cls) -> Sequence[str]:
        stmt = (
            db.select(cls.id)
            .join(BotParameterValue, cls.id == BotParameterValue.bot_id)
            .join(ParameterValue, BotParameterValue.parameter_value_id == ParameterValue.id)
            .filter(db.and_(ParameterValue.parameter == "RUN_AFTER_COLLECTOR", ParameterValue.value == "true"))
            .order_by(cls.index)
        )

        return db.session.execute(stmt).scalars().all()

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["parameters"] = {parameter.parameter: parameter.value for parameter in self.parameters}
        return data

    def schedule_bot(self):
        if interval := ParameterValue.find_value_by_parameter(self.parameters, "REFRESH_INTERVAL"):
            entry = self.to_task_dict(interval)
            ScheduleEntry.add_or_update(entry)
            logger.info(f"Schedule for bot {self.id} updated with - {entry}")
            return {"message": f"Schedule for bot {self.id} updated"}, 200
        return {"message": "Bot has no refresh interval"}, 200

    def unschedule_bot(self):
        entry_id = f"bot_{self.id}_{self.type}"
        ScheduleEntry.delete(entry_id)
        logger.info(f"Schedule for bot {self.id} removed")
        return {"message": f"Schedule for bot {self.id} removed"}, 200

    def to_task_dict(self, interval):
        return {
            "id": f"bot_{self.id}_{self.type}",
            "task": "bot_task",
            "schedule": interval,
            "args": [self.id],
            "options": {"queue": "bots"},
        }

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.filter(db.or_(Bot.name.ilike(f"%{search}%"), Bot.description.ilike(f"%{search}%")))

        return query


class BotParameterValue(BaseModel):
    bot_id: Mapped[str] = db.Column(db.String, db.ForeignKey("bot.id", ondelete="CASCADE"), primary_key=True)
    parameter_value_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
