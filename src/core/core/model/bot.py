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
    type: Mapped[BOT_TYPES] = db.Column(db.Enum(BOT_TYPES), nullable=False)
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
    def filter_by_type(cls, filter_type: str | BOT_TYPES) -> "Bot | None":
        try:
            bot_type = cls.normalize_bot_type(filter_type)
        except ValueError:
            return None
        try:
            return db.session.execute(db.select(cls).where(cls.type == bot_type).order_by(cls.index)).scalars().first()
        except Exception:
            logger.exception(f"Error filtering bots by type: {filter_type}")
            return None

    @classmethod
    def get_all_by_type(cls, filter_type: str | BOT_TYPES) -> Sequence["Bot"]:
        try:
            bot_type = cls.normalize_bot_type(filter_type)
        except ValueError:
            return []
        return cls.get_filtered(db.select(cls).where(cls.type == bot_type).order_by(cls.index)) or []

    @classmethod
    def get_post_collection(cls) -> Sequence[str]:
        bots, _ = cls.get_collector_run_graph()
        return [bot.id for bot in bots]

    @classmethod
    def get_collector_run_graph(cls) -> tuple[list["Bot"], dict[str, list[str]]]:
        return cls._get_run_graph()

    @classmethod
    def get_dependent_run_graph(cls, completed_bot_id: str) -> tuple[list["Bot"], dict[str, list[str]]]:
        return cls._get_run_graph(after_bot_id=completed_bot_id)

    @classmethod
    def _get_run_graph(cls, after_bot_id: str | None = None) -> tuple[list["Bot"], dict[str, list[str]]]:
        bots_by_id = {bot.id: bot for bot in cls._get_all_ordered()}
        enabled_bots_by_id = {bot_id: bot for bot_id, bot in bots_by_id.items() if bot.enabled}
        dependencies = cls._dependency_map(bots_by_id)
        order, scheduled_dependencies = cls._build_run_graph(
            enabled_bots_by_id,
            dependencies,
            after_bot_id=after_bot_id,
        )
        return [enabled_bots_by_id[bot_id] for bot_id in order], {bot_id: list(scheduled_dependencies[bot_id]) for bot_id in order}

    @classmethod
    def _build_run_graph(
        cls,
        bots_by_id: dict[str, "Bot"],
        dependencies: dict[str, set[str]],
        after_bot_id: str | None = None,
    ) -> tuple[list[str], dict[str, tuple[str, ...]]]:
        if after_bot_id is None:
            scheduled = {bot_id for bot_id, bot in bots_by_id.items() if bot.run_after_collector}
        else:
            scheduled = {bot_id for bot_id, parents in dependencies.items() if bot_id in bots_by_id and after_bot_id in parents}

        scheduled = cls._reachable_bot_ids(scheduled, dependencies, set(bots_by_id))
        if not scheduled:
            return [], {}

        def sort_key(bot_id: str) -> int:
            return bots_by_id[bot_id].index

        graph = {
            bot_id: tuple(sorted(dependencies.get(bot_id, set()) & scheduled, key=sort_key)) for bot_id in sorted(scheduled, key=sort_key)
        }
        return cls._topological_order(graph), graph

    @staticmethod
    def _reachable_bot_ids(start_ids: set[str], dependencies: dict[str, set[str]], enabled_ids: set[str]) -> set[str]:
        scheduled = set(start_ids)
        pending = list(start_ids)
        while pending:
            parent_id = pending.pop()
            for bot_id, parents in dependencies.items():
                if bot_id in enabled_ids and parent_id in parents and bot_id not in scheduled:
                    scheduled.add(bot_id)
                    pending.append(bot_id)
        return scheduled

    @staticmethod
    def _topological_order(graph: dict[str, tuple[str, ...]]) -> list[str]:
        try:
            return list(TopologicalSorter(graph).static_order())
        except CycleError as exc:
            cycle = " -> ".join(str(item) for item in exc.args[1])
            raise ValueError(f"Bot run order contains a cycle: {cycle}") from exc

    @classmethod
    def _get_all_ordered(cls) -> list["Bot"]:
        return list(db.session.execute(db.select(cls).order_by(cls.index)).scalars().all())

    @classmethod
    def _dependency_map(cls, bots_by_id: dict[str, "Bot"]) -> dict[str, set[str]]:
        dependencies: dict[str, set[str]] = {bot_id: set() for bot_id in bots_by_id}
        for bot_id, bot in bots_by_id.items():
            for parent_id in bot.run_after_bot_ids:
                if parent_id == bot_id:
                    raise ValueError(f"{bot.name} cannot run after itself")
                dependencies[bot_id].add(parent_id)
        return dependencies

    @classmethod
    def validate_dependency_config(cls) -> None:
        bots_by_id = {bot.id: bot for bot in cls._get_all_ordered()}
        dependencies = cls._dependency_map(bots_by_id)

        def sort_key(bot_id: str) -> int:
            return bots_by_id[bot_id].index

        graph = {
            bot_id: tuple(sorted(parents & set(bots_by_id), key=sort_key))
            for bot_id, parents in sorted(dependencies.items(), key=lambda item: sort_key(item[0]))
        }
        cls._topological_order(graph)

    @staticmethod
    def normalize_bot_type(value: str | BOT_TYPES) -> BOT_TYPES:
        if isinstance(value, BOT_TYPES):
            return value
        try:
            return BOT_TYPES(str(value).strip())
        except ValueError as exc:
            raise ValueError(f"Unknown bot type: {value}") from exc

    @staticmethod
    def parse_run_after_bots(value: Any) -> tuple[str, ...]:
        if isinstance(value, list):
            raw_values = value
        else:
            raw_values = str(value or "").split(",")
        result: list[str] = []
        for raw_value in raw_values:
            if not (value_text := str(raw_value).strip()):
                continue
            try:
                bot_id = Bot.normalize_uuid_id(value_text)
            except ValueError as exc:
                raise ValueError(f"Invalid bot ID: {value_text}") from exc
            if bot_id not in result:
                result.append(bot_id)
        return tuple(result)

    @property
    def parameter_map(self) -> dict[str, str]:
        return {parameter.parameter: parameter.value for parameter in self.parameters}

    @property
    def run_after_collector(self) -> bool:
        return self.parameter_map.get(RUN_AFTER_COLLECTOR, "").lower() == "true"

    @property
    def run_after_bot_ids(self) -> tuple[str, ...]:
        return self.parse_run_after_bots(self.parameter_map.get(RUN_AFTER_BOTS, ""))

    @classmethod
    def get_dag_preview(cls, candidate: dict[str, Any]) -> dict[str, Any]:
        bots = cls._get_all_ordered()
        allowed_fields = {"id", "type", "index", "enabled", "parameters"}
        if unexpected_fields := set(candidate) - allowed_fields:
            raise ValueError(f"Unexpected bot DAG preview fields: {', '.join(sorted(unexpected_fields))}")

        parameters = candidate.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ValueError("Bot DAG preview parameters must be an object")
        if unexpected_parameters := set(parameters) - {RUN_AFTER_COLLECTOR, RUN_AFTER_BOTS}:
            raise ValueError(f"Unexpected bot DAG preview parameters: {', '.join(sorted(unexpected_parameters))}")

        bot_type = cls.normalize_bot_type(candidate.get("type", ""))
        candidate_id = candidate.get("id") or None
        stored_bot = next((bot for bot in bots if bot.id == candidate_id), None)
        index = candidate.get("index")
        candidate_bot = cls.from_dict(
            {
                "id": stored_bot.id if stored_bot else candidate_id,
                "name": stored_bot.name if stored_bot else "Unsaved bot",
                "description": stored_bot.description if stored_bot else "",
                "type": bot_type.value,
                "index": int(index) if index not in ("", None) else stored_bot.index if stored_bot else cls.get_highest_index() + 1,
                "enabled": str(candidate.get("enabled", stored_bot.enabled if stored_bot else True)).lower() == "true",
                "parameters": parameters,
            }
        )
        bots = [bot for bot in bots if bot.id != candidate_bot.id]
        bots.append(candidate_bot)
        bots.sort(key=lambda bot: bot.index)

        warnings_by_id: list[tuple[str, str]] = []
        bots_by_id = {bot.id: bot for bot in bots}
        dependencies: dict[str, set[str]] = {bot.id: set() for bot in bots}
        edges: list[dict[str, Any]] = []
        for bot_id, bot in bots_by_id.items():
            try:
                parent_ids = bot.run_after_bot_ids
            except ValueError as exc:
                warnings_by_id.append((bot_id, str(exc)))
                continue
            for parent_id in parent_ids:
                if parent_id == bot_id:
                    warnings_by_id.append((bot_id, f"{bot.name} cannot run after itself"))
                    continue
                dependencies[bot_id].add(parent_id)
                parent_bot = bots_by_id.get(parent_id)
                if not parent_bot:
                    warnings_by_id.append((bot_id, f"{bot.name} waits for missing bot {parent_id}"))
                    continue
                if not parent_bot.enabled:
                    warnings_by_id.append((bot_id, f"{bot.name} waits for disabled bot {parent_bot.name}"))
                edges.append(
                    {
                        "from_id": parent_id,
                        "from_type": parent_bot.type.name,
                        "from_name": parent_bot.name,
                        "to_id": bot_id,
                        "to_type": bot.type.name,
                        "to_name": bot.name,
                        "disabled": not parent_bot.enabled or not bot.enabled,
                    }
                )

        related_ids = {candidate_bot.id}
        changed = True
        while changed:
            changed = False
            for edge in edges:
                edge_ids = {edge["from_id"], edge["to_id"]}
                if related_ids & edge_ids and not edge_ids <= related_ids:
                    related_ids.update(edge_ids)
                    changed = True

        edges = [edge for edge in edges if edge["from_id"] in related_ids and edge["to_id"] in related_ids]
        warnings = [warning for bot_id, warning in warnings_by_id if bot_id in related_ids]
        enabled_by_id = {bot_id: bot for bot_id, bot in bots_by_id.items() if bot.enabled}
        try:
            cls._topological_order(
                {bot_id: tuple(parent_ids & related_ids) for bot_id, parent_ids in dependencies.items() if bot_id in related_ids}
            )
            order, _ = cls._build_run_graph(enabled_by_id, dependencies)
            if candidate_bot.id not in order:
                order = []
        except ValueError as exc:
            warnings.append(str(exc))
            order = []

        return {
            "order": [
                {
                    "id": bot_id,
                    "type": enabled_by_id[bot_id].type.name,
                    "name": enabled_by_id[bot_id].name,
                    "enabled": enabled_by_id[bot_id].enabled,
                }
                for bot_id in order
            ],
            "edges": edges,
            "warnings": list(dict.fromkeys(warnings)),
            "nodes": [
                {"id": bot.id, "type": bot.type.name, "name": bot.name, "enabled": bot.enabled}
                for bot in sorted(bots_by_id.values(), key=lambda item: item.index)
                if bot.id in related_ids
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
