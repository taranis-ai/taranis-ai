from datetime import datetime
from graphlib import CycleError, TopologicalSorter
from typing import Any, Sequence

from models.admin import CronSpec
from models.types import BOT_TYPES
from sqlalchemy import func
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import Select

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel
from core.model.parameter_value import ParameterValue
from core.model.task import Task as TaskModel
from core.model.worker import Worker


RUN_AFTER_COLLECTOR = "RUN_AFTER_COLLECTOR"
RUN_AFTER_BOTS = "RUN_AFTER_BOTS"


class Bot(BaseModel):
    __tablename__ = "bot"

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    name: Mapped[str] = db.Column(db.String(), nullable=False)
    description: Mapped[str] = db.Column(db.String())
    type: Mapped[BOT_TYPES] = db.Column(db.Enum(BOT_TYPES), unique=True, nullable=False)
    index: Mapped[int] = db.Column(db.Integer, unique=True, nullable=False)
    enabled: Mapped[bool] = db.Column(db.Boolean, default=True)
    parameters: Mapped[list[ParameterValue]] = relationship("ParameterValue", secondary="bot_parameter_value", cascade="all, delete")

    def __init__(
        self,
        name: str,
        type: str | BOT_TYPES,
        description: str = "",
        index: int | None = None,
        parameters=None,
        enabled: bool = True,
        id: str | None = None,
    ):
        self.id = self.normalize_uuid_id(id)
        self.name = name
        self.description = description
        self.type = type if isinstance(type, BOT_TYPES) else BOT_TYPES(type.lower())
        self.index = index or Bot.get_highest_index() + 1
        self.enabled = enabled
        self.parameters = Worker.parse_parameters(type, parameters)

    @property
    def status(self):
        if task_result := TaskModel.get_latest_matching(
            exact_ids={self.task_id},
            prefixes=[self.cron_run_prefix],
            task_name=self.task_id,
        ):
            return task_result.to_dict()
        return None

    @property
    def task_id(self):
        return f"bot_{self.id}"

    @property
    def cron_job_id(self) -> str:
        return f"bot_{self.id}"

    @property
    def cron_run_prefix(self) -> str:
        return f"cron_{self.cron_job_id}_"

    @classmethod
    def add(cls, data):
        try:
            bot = cls.from_dict(data)
            cls._validate_unique_type(bot.type, bot.id)
            db.session.add(bot)
            cls.validate_dependency_config()
            db.session.commit()
            bot.schedule_bot()
            return bot
        except Exception:
            db.session.rollback()
            raise

    @classmethod
    def update(cls, bot_id: str, data: dict[str, Any]) -> "Bot | None":
        bot = cls.get(bot_id)
        if not bot:
            return None
        try:
            if name := data.get("name"):
                bot.name = name

            bot.description = data.get("description", "")
            if "type" in data:
                bot.type = cls.normalize_bot_type(data["type"])
                cls._validate_unique_type(bot.type, bot.id)
            if "enabled" in data:
                bot.enabled = data.get("enabled", True)
            if parameters := data.get("parameters"):
                update_parameter = ParameterValue.get_or_create_from_list(parameters)
                bot.parameters = ParameterValue.get_update_values(bot.parameters, update_parameter)
            if index := data.get("index"):
                if not Bot.index_exists(index):
                    bot.index = index
            cls.validate_dependency_config()
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        bot._refresh_schedule_registration()

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
        try:
            bot_type = cls.normalize_bot_type(filter_type)
        except ValueError:
            return None
        try:
            return db.session.execute(db.select(cls).where(cls.type == bot_type)).scalar_one_or_none()
        except Exception:
            logger.exception(f"Error filtering bots by type: {filter_type}")
            return None

    @classmethod
    def get_all_by_type(cls, filter_type: str):
        return cls.get_filtered(db.select(cls).where(cls.type == filter_type))

    @classmethod
    def get_post_collection(cls) -> Sequence[str]:
        bots, _ = cls.get_collector_run_graph()
        return [bot.id for bot in bots]

    @classmethod
    def get_collector_run_graph(cls) -> tuple[list["Bot"], dict[str, list[str]]]:
        return cls._get_run_graph()

    @classmethod
    def get_dependent_run_graph(cls, completed_bot_type: str | BOT_TYPES) -> tuple[list["Bot"], dict[str, list[str]]]:
        return cls._get_run_graph(after_bot_type=completed_bot_type)

    @classmethod
    def _get_run_graph(cls, after_bot_type: str | BOT_TYPES | None = None) -> tuple[list["Bot"], dict[str, list[str]]]:
        bots_by_type = cls._bot_type_map(cls.get_all_for_collector())
        dependencies = cls._dependency_map(bots_by_type)
        order, dependency_types = cls._build_run_graph(bots_by_type, dependencies, after_bot_type=after_bot_type)
        bots = [bots_by_type[bot_type] for bot_type in order]
        dependencies_by_id = {
            bots_by_type[bot_type].id: [bots_by_type[parent_type].id for parent_type in dependency_types[bot_type]] for bot_type in order
        }
        return bots, dependencies_by_id

    @classmethod
    def _build_run_graph(
        cls,
        bots_by_type: dict[BOT_TYPES, "Bot"],
        dependencies: dict[BOT_TYPES, set[BOT_TYPES]],
        after_bot_type: str | BOT_TYPES | None = None,
    ) -> tuple[list[BOT_TYPES], dict[BOT_TYPES, tuple[BOT_TYPES, ...]]]:
        if after_bot_type is None:
            scheduled = {bot_type for bot_type, bot in bots_by_type.items() if bot.run_after_collector}
        else:
            completed_type = cls.normalize_bot_type(after_bot_type)
            scheduled = {bot_type for bot_type, parents in dependencies.items() if completed_type in parents}

        scheduled = cls._reachable_types(scheduled, dependencies)
        if not scheduled:
            return [], {}

        def sort_key(bot_type: BOT_TYPES) -> int:
            return bots_by_type[bot_type].index

        graph = {
            bot_type: tuple(sorted(dependencies.get(bot_type, set()) & scheduled, key=sort_key))
            for bot_type in sorted(scheduled, key=sort_key)
        }
        return cls._topological_order(graph), graph

    @staticmethod
    def _reachable_types(start_types: set[BOT_TYPES], dependencies: dict[BOT_TYPES, set[BOT_TYPES]]) -> set[BOT_TYPES]:
        scheduled = set(start_types)
        pending = list(start_types)
        while pending:
            parent_type = pending.pop()
            for bot_type, parents in dependencies.items():
                if parent_type in parents and bot_type not in scheduled:
                    scheduled.add(bot_type)
                    pending.append(bot_type)
        return scheduled

    @staticmethod
    def _topological_order(graph: dict[BOT_TYPES, tuple[BOT_TYPES, ...]]) -> list[BOT_TYPES]:
        try:
            return list(TopologicalSorter(graph).static_order())
        except CycleError as exc:
            cycle = " -> ".join(item.name if isinstance(item, BOT_TYPES) else str(item) for item in exc.args[1])
            raise ValueError(f"Bot run order contains a cycle: {cycle}") from exc

    @classmethod
    def _get_all_ordered(cls) -> list["Bot"]:
        return list(db.session.execute(db.select(cls).order_by(cls.index)).scalars().all())

    @classmethod
    def _bot_type_map(cls, bots: Sequence["Bot"]) -> dict[BOT_TYPES, "Bot"]:
        bots_by_type: dict[BOT_TYPES, Bot] = {}
        for bot in bots:
            if bot.type in bots_by_type:
                raise ValueError(f"Only one bot per type is allowed: {bot.type.name}")
            bots_by_type[bot.type] = bot
        return bots_by_type

    @classmethod
    def _dependency_map(cls, bots_by_type: dict[BOT_TYPES, "Bot"]) -> dict[BOT_TYPES, set[BOT_TYPES]]:
        dependencies: dict[BOT_TYPES, set[BOT_TYPES]] = {bot_type: set() for bot_type in bots_by_type}
        for bot_type, bot in bots_by_type.items():
            for parent_type in bot.run_after_bot_types:
                if parent_type == bot_type:
                    raise ValueError(f"{bot_type.name} cannot run after itself")
                if parent_type in bots_by_type:
                    dependencies[bot_type].add(parent_type)
        return dependencies

    @classmethod
    def validate_dependency_config(cls) -> None:
        bots_by_type = cls._bot_type_map(cls._get_all_ordered())
        dependencies = cls._dependency_map(bots_by_type)

        def sort_key(bot_type: BOT_TYPES) -> int:
            return bots_by_type[bot_type].index

        graph = {
            bot_type: tuple(sorted(parents, key=sort_key))
            for bot_type, parents in sorted(dependencies.items(), key=lambda item: sort_key(item[0]))
        }
        cls._topological_order(graph)

    @classmethod
    def _validate_unique_type(cls, bot_type: BOT_TYPES, bot_id: str | None = None) -> None:
        with db.session.no_autoflush:
            existing = cls.filter_by_type(bot_type.value)
        if existing and existing.id != bot_id:
            raise ValueError(f"Bot type {bot_type.name} already exists")

    @staticmethod
    def normalize_bot_type(value: str | BOT_TYPES) -> BOT_TYPES:
        if isinstance(value, BOT_TYPES):
            return value
        try:
            return BOT_TYPES(str(value).strip())
        except ValueError as exc:
            raise ValueError(f"Unknown bot type: {value}") from exc

    @staticmethod
    def parse_run_after_bots(value: Any) -> tuple[BOT_TYPES, ...]:
        if isinstance(value, list):
            raw_values = value
        else:
            raw_values = str(value or "").split(",")
        result: list[BOT_TYPES] = []
        for raw_value in raw_values:
            if not (value_text := str(raw_value).strip()):
                continue
            bot_type = Bot.normalize_bot_type(value_text)
            if bot_type not in result:
                result.append(bot_type)
        return tuple(result)

    @property
    def parameter_map(self) -> dict[str, str]:
        return {parameter.parameter: parameter.value for parameter in self.parameters}

    @property
    def run_after_collector(self) -> bool:
        return self.parameter_map.get(RUN_AFTER_COLLECTOR, "").lower() == "true"

    @property
    def run_after_bot_types(self) -> tuple[BOT_TYPES, ...]:
        return self.parse_run_after_bots(self.parameter_map.get(RUN_AFTER_BOTS, ""))

    @classmethod
    def get_dag_preview(cls, candidate: dict[str, Any]) -> dict[str, Any]:
        bots = cls._get_all_ordered()
        allowed_fields = {"type", "index", "enabled", "parameters"}
        if unexpected_fields := set(candidate) - allowed_fields:
            raise ValueError(f"Unexpected bot DAG preview fields: {', '.join(sorted(unexpected_fields))}")

        parameters = candidate.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ValueError("Bot DAG preview parameters must be an object")
        if unexpected_parameters := set(parameters) - {RUN_AFTER_COLLECTOR, RUN_AFTER_BOTS}:
            raise ValueError(f"Unexpected bot DAG preview parameters: {', '.join(sorted(unexpected_parameters))}")

        bot_type = cls.normalize_bot_type(candidate.get("type", ""))
        stored_bot = next((bot for bot in bots if bot.type == bot_type), None)
        index = candidate.get("index")
        candidate_bot = cls.from_dict(
            {
                "id": stored_bot.id if stored_bot else None,
                "name": stored_bot.name if stored_bot else "Unsaved bot",
                "description": stored_bot.description if stored_bot else "",
                "type": bot_type.value,
                "index": int(index) if index not in ("", None) else stored_bot.index if stored_bot else cls.get_highest_index() + 1,
                "enabled": str(candidate.get("enabled", stored_bot.enabled if stored_bot else True)).lower() == "true",
                "parameters": parameters,
            }
        )
        bots = [bot for bot in bots if bot.id != candidate_bot.id and bot.type != candidate_bot.type]
        bots.append(candidate_bot)
        bots.sort(key=lambda bot: bot.index)

        warnings_by_type: list[tuple[str, str]] = []
        bots_by_type: dict[BOT_TYPES, Bot] = {}
        for bot in bots:
            if bot.type in bots_by_type:
                warnings_by_type.append((bot.type.name, f"Duplicate bot type configured: {bot.type.name}"))
            bots_by_type[bot.type] = bot

        edges = []
        for bot_type, bot in bots_by_type.items():
            try:
                parent_types = bot.run_after_bot_types
            except ValueError as exc:
                warnings_by_type.append((bot_type.name, str(exc)))
                continue
            for parent_type in parent_types:
                if parent_type == bot_type:
                    warnings_by_type.append((bot_type.name, f"{bot_type.name} cannot run after itself"))
                    continue
                parent_bot = bots_by_type.get(parent_type)
                if not parent_bot:
                    warnings_by_type.append((bot_type.name, f"{bot_type.name} waits for missing bot type {parent_type.name}"))
                    continue
                if not parent_bot.enabled:
                    warnings_by_type.append((bot_type.name, f"{bot_type.name} waits for disabled bot {parent_bot.name}"))
                edges.append(
                    {
                        "from_type": parent_type.name,
                        "from_name": parent_bot.name,
                        "to_type": bot_type.name,
                        "to_name": bot.name,
                        "disabled": not parent_bot.enabled or not bot.enabled,
                    }
                )

        related_types = {candidate_bot.type.name}
        changed = True
        while changed:
            changed = False
            for edge in edges:
                edge_types = {edge["from_type"], edge["to_type"]}
                if related_types & edge_types and not edge_types <= related_types:
                    related_types.update(edge_types)
                    changed = True

        edges = [edge for edge in edges if edge["from_type"] in related_types and edge["to_type"] in related_types]
        warnings = [warning for bot_type, warning in warnings_by_type if bot_type in related_types]
        enabled_by_type = {bot_type: bot for bot_type, bot in bots_by_type.items() if bot.enabled}
        try:
            dependencies = cls._dependency_map(enabled_by_type)
            order, _ = cls._build_run_graph(enabled_by_type, dependencies)
            if candidate_bot.type not in order:
                order = []
        except ValueError as exc:
            warnings.append(str(exc))
            order = []

        return {
            "order": [
                {
                    "type": bot_type.name,
                    "name": enabled_by_type[bot_type].name,
                    "enabled": enabled_by_type[bot_type].enabled,
                }
                for bot_type in order
            ],
            "edges": edges,
            "warnings": list(dict.fromkeys(warnings)),
            "nodes": [
                {"type": bot.type.name, "name": bot.name, "enabled": bot.enabled}
                for bot in sorted(bots_by_type.values(), key=lambda item: item.index)
                if bot.type.name in related_types
            ],
        }

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["parameters"] = self.parameter_map
        if self.status:
            data["status"] = self.status
        return data

    @classmethod
    def delete(cls, id: str) -> tuple[dict[str, Any], int]:
        from core.managers import queue_manager

        bot = cls.get(id)
        if not bot:
            return {"error": "Bot not found"}, 404

        bot.unschedule_bot()
        queue_manager.queue_manager.purge_job_artifacts(
            exact_ids={bot.task_id},
            prefixes=[bot.cron_run_prefix],
        )
        db.session.delete(bot)
        db.session.commit()
        return {"message": "Bot deleted"}, 200

    def get_schedule(self) -> str:
        return ParameterValue.find_value_by_parameter(self.parameters, "REFRESH_INTERVAL")

    def get_cron_spec(self) -> CronSpec:
        return CronSpec(
            meta={
                "name": f"Bot: {self.name}",
                "task": self.task_id,
                "worker_id": self.id,
                "worker_type": self.type.value.upper(),
            },
            job_id=self.cron_job_id,
            cron=self.get_schedule(),
            func_path="bot_task",
            args=[self.id],
            queue_name="bots",
        )

    def schedule_bot(self):
        from core.managers import queue_manager

        cron_schedule = self.get_schedule()
        if not self.enabled or not cron_schedule:
            return False

        return queue_manager.queue_manager.register_cron_job(self.get_cron_spec())

    def unschedule_bot(self):
        from core.managers import queue_manager

        return queue_manager.queue_manager.unregister_cron_job(self.cron_job_id)

    @classmethod
    def get_enabled_schedule_entries(cls, now: datetime | None = None) -> list[dict[str, Any]]:
        """Get schedule entries for all enabled bots.

        Note: All times are calculated in UTC for consistency across the system.
        """
        from datetime import timezone

        from core.managers import queue_manager as queue_manager_module
        from core.managers.queue_manager import QueueManager

        now = now or datetime.now(timezone.utc).replace(tzinfo=None)
        entries: list[dict[str, Any]] = []

        bots = cls.get_all_for_collector()
        for bot in bots:
            if not (cron_schedule := bot.get_schedule()):
                continue

            try:
                task_result = TaskModel.get_latest_matching(
                    exact_ids={bot.task_id},
                    prefixes=[bot.cron_run_prefix],
                    task_name=bot.task_id,
                )

                entries.append(
                    QueueManager.build_cron_schedule_entry(
                        job_id=bot.cron_job_id,
                        name=f"Bot: {bot.name}",
                        queue="bots",
                        cron_schedule=cron_schedule,
                        now=now,
                        bot_id=bot.id,
                        task_id=bot.task_id,
                        last_run=task_result.last_run if task_result else None,
                        last_success=task_result.last_success if task_result else None,
                        last_status=task_result.status if task_result else None,
                        last_reason=queue_manager_module._task_result_reason(task_result),
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
        query = db.select(cls).where(cls.enabled.is_(True)).order_by(cls.index)
        return db.session.execute(query).scalars().all()

    @classmethod
    def schedule_all_bots(cls):
        """Schedule all enabled bots with cron definitions."""
        bots = cls.get_all_for_collector()
        enabled_with_schedule = [bot for bot in bots if bot.get_schedule()]
        for bot in enabled_with_schedule:
            bot.schedule_bot()
        logger.info(f"Scheduling for {len(enabled_with_schedule)} bots completed")

    def _refresh_schedule_registration(self) -> None:
        if self.enabled and self.get_schedule():
            self.schedule_bot()
        else:
            self.unschedule_bot()


class BotParameterValue(BaseModel):
    bot_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("bot.id", ondelete="CASCADE"), primary_key=True)
    parameter_value_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("parameter_value.id"), primary_key=True)
