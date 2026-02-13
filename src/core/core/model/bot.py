import uuid
from datetime import datetime
from typing import Any, Sequence

from models.types import BOT_TYPES
from sqlalchemy import func
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import Select

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import BaseModel
from core.model.parameter_value import ParameterValue
from core.model.task import Task as TaskModel
from core.model.worker import Worker


class Bot(BaseModel):
    __tablename__ = "bot"

    id: Mapped[str] = db.Column(db.String(64), primary_key=True)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())
    type: Mapped[BOT_TYPES] = db.Column(db.Enum(BOT_TYPES))
    index: Mapped[int] = db.Column(db.Integer, unique=True, nullable=False)
    enabled: Mapped[bool] = db.Column(db.Boolean, default=True)
    parameters: Mapped[list[ParameterValue]] = relationship("ParameterValue", secondary="bot_parameter_value", cascade="all, delete")

    def __init__(
        self, name: str, type: str | BOT_TYPES, description: str = "", index: int | None = None, parameters=None, id: str | None = None
    ):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.type = type if isinstance(type, BOT_TYPES) else BOT_TYPES(type.lower())
        self.index = index or Bot.get_highest_index() + 1
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
    def update(cls, bot_id: str, data: dict[str, Any]) -> "Bot | None":
        bot = cls.get(bot_id)
        if not bot:
            return None
        if name := data.get("name"):
            bot.name = name

        bot.description = data.get("description", "")
        if parameters := data.get("parameters"):
            update_parameter = ParameterValue.get_or_create_from_list(parameters)
            bot.parameters = ParameterValue.get_update_values(bot.parameters, update_parameter)
        if index := data.get("index"):
            if not Bot.index_exists(index):
                bot.index = index
        db.session.commit()

        # Notify cron scheduler of config change
        bot._publish_cron_reload(f"bot_{bot_id}")

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
        db.session.delete(bot)
        db.session.commit()
        return {"message": f"Bot {bot.name} deleted"}, 200

    def get_schedule(self) -> str:
        return ParameterValue.find_value_by_parameter(self.parameters, "REFRESH_INTERVAL")

    @classmethod
    def get_enabled_schedule_entries(cls, now: datetime | None = None) -> list[dict[str, Any]]:
        """Get schedule entries for all enabled bots.

        Note: All times are calculated in UTC for consistency across the system.
        """
        from datetime import timezone

        from core.managers.queue_manager import QueueManager

        now = now or datetime.now(timezone.utc).replace(tzinfo=None)
        entries: list[dict[str, Any]] = []

        bots = cls.get_all_for_collector()
        for bot in bots:
            if not (cron_schedule := bot.get_schedule()):
                continue

            try:
                status = bot.status or {}

                entries.append(
                    QueueManager.build_cron_schedule_entry(
                        job_id=f"cron_bot_{bot.id}",
                        name=f"Bot: {bot.name}",
                        queue="bots",
                        cron_schedule=cron_schedule,
                        now=now,
                        stringify_times=True,
                        bot_id=bot.id,
                        task_id=bot.task_id,
                        last_run=status.get("last_run"),
                        last_success=status.get("last_success"),
                        last_status=status.get("status"),
                    )
                )
            except Exception as exc:
                logger.error(f"Failed to calculate next run for bot {bot.id}: {exc}")

        return entries

    @classmethod
    def get_filter_query(cls, filter_args: dict[str, Any]) -> Select:
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
        """Schedule all enabled bots using RQ cron scheduler

        Note: Just logs - the cron scheduler automatically picks up bots from database.
        """
        bots = cls.get_all_for_collector()
        enabled_with_schedule = [bot for bot in bots if bot.get_schedule()]
        logger.info(f"Found {len(enabled_with_schedule)} enabled bots with schedules. Cron scheduler will pick them up automatically.")

    def _publish_cron_reload(self, reason: str):
        """Publish a signal to reload cron scheduler configuration"""
        try:
            from core.managers import queue_manager

            qm = queue_manager.queue_manager
            if qm.error or not qm._redis:
                return

            # Publish reload signal to cron scheduler
            qm._redis.publish("taranis:cron:reload", reason)
            logger.debug(f"Published cron reload signal: {reason}")

            # Publish cache invalidation signal to frontend
            qm._redis.publish("taranis:cache:invalidate", "schedule")
            logger.debug("Published cache invalidation signal for schedules")

        except Exception as e:
            logger.warning(f"Failed to publish cron reload signal: {e}")


class BotParameterValue(BaseModel):
    bot_id: Mapped[str] = db.Column(db.String, db.ForeignKey("bot.id", ondelete="CASCADE"), primary_key=True)
    parameter_value_id: Mapped[int] = db.Column(db.Integer, db.ForeignKey("parameter_value.id"), primary_key=True)
