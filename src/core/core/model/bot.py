import uuid
from typing import Any, Sequence

from sqlalchemy import func
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import Select
from apscheduler.triggers.cron import CronTrigger

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.parameter_value import ParameterValue
from core.model.worker import BOT_TYPES, Worker
from core.managers import schedule_manager
from core.model.task import Task as TaskModel


class Bot(BaseModel):
    __tablename__ = "bot"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())
    type: Mapped[BOT_TYPES] = db.Column(db.Enum(BOT_TYPES))
    index: Mapped[int] = db.Column(db.Integer, unique=True, nullable=False)
    enabled: Mapped[bool] = db.Column(db.Boolean, default=True)
    parameters: Mapped[list[ParameterValue]] = relationship("ParameterValue", secondary="bot_parameter_value", cascade="all, delete")

    def __init__(self, name: str, type: str | BOT_TYPES, description: str = "", parameters=None, id: str | None = None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type if isinstance(type, BOT_TYPES) else BOT_TYPES(type.lower())
        self.index = Bot.get_highest_index() + 1
        self.parameters = Worker.parse_parameters(type, parameters)

    @property
    def status(self):
        if task_result := TaskModel.get(self.task_id):
            return task_result.to_dict()
        return None

    @property
    def task_id(self):
        return f"bot_{self.id}"

    @classmethod
    def update(cls, bot_id, data) -> "Bot | None":
        bot = cls.get(bot_id)
        if not bot:
            return None
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
        bot.unschedule_bot()
        bot.schedule_bot()
        return bot

    @classmethod
    def get_highest_index(cls):
        result = db.session.query(func.max(cls.index)).scalar()
        return result or 0

    @classmethod
    def index_exists(cls, index):
        query = db.select(db.exists().where(cls.index == index))
        return db.session.execute(query).scalar_one()

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
        if self.status:
            data["status"] = self.status
        return data

    @classmethod
    def delete(cls, id: str) -> tuple[dict[str, Any], int]:
        bot = cls.get(id)
        if not bot:
            return {"error": "Bot not found"}, 404

        TaskModel.delete(bot.task_id)
        bot.unschedule_bot()
        db.session.delete(bot)
        db.session.commit()
        return {"message": f"Bot {bot.name} deleted"}, 200

    def schedule_bot(self):
        if crontab_str := self.get_schedule():
            entry = self.to_task_dict(crontab_str)
            schedule_manager.schedule.add_prefect_task(entry)
            logger.info(f"Schedule for bot {self.id} updated with - {entry}")
            return {"message": f"Schedule for bot {self.id} updated"}, 200
        return {"message": "Bot has no refresh interval"}, 200

    def unschedule_bot(self):
        entry_id = self.task_id
        schedule_manager.schedule.remove_periodic_task(entry_id)
        logger.info(f"Schedule for bot {self.id} removed")
        return {"message": f"Schedule for bot {self.id} removed"}, 200

    def get_schedule(self) -> str:
        return ParameterValue.find_value_by_parameter(self.parameters, "REFRESH_INTERVAL")

    def to_task_dict(self, crontab_str: str) -> dict[str, Any]:
        return {
            "id": self.task_id,
            "name": f"{self.type}_{self.name}",
            "jobs_params": {
                "trigger": CronTrigger.from_crontab(crontab_str),
                "max_instances": 1,
            },
            "celery": {
                "name": "bot_task",
                "args": [self.id],
                "queue": "bots",
                "task_id": self.task_id,
            },
        }

    @classmethod
    def get_filter_query(cls, filter_args: dict) -> Select:
        query = db.select(cls)

        if search := filter_args.get("search"):
            query = query.filter(db.or_(Bot.name.ilike(f"%{search}%"), Bot.description.ilike(f"%{search}%")))

        return query

    @classmethod
    def get_all_for_collector(cls) -> Sequence["Bot"]:
        query = db.select(cls).where(cls.enabled.is_(True)).distinct(cls.id)
        return db.session.execute(query).scalars().all()

    @classmethod
    def schedule_all_bots(cls):
        bots = cls.get_all_for_collector()
        for bot in bots:
            if interval := bot.get_schedule():
                entry = bot.to_task_dict(interval)
                schedule_manager.schedule.add_prefect_task(entry)
        logger.info(f"Gathering for {len(bots)} Bots scheduled")


class BotParameterValue(BaseModel):
    bot_id: Mapped[str] = db.Column(db.String, db.ForeignKey("bot.id", ondelete="CASCADE"), primary_key=True)
    parameter_value_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
