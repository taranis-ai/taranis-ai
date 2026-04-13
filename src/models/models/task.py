from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from models.base import TaranisBaseModel


class CronTaskSpec(TaranisBaseModel):
    queue_name: str
    func_path: str
    cron: str | None = None
    interval: int | None = None
    args: list[Any] = Field(default_factory=list)
    kwargs: dict[str, Any] = Field(default_factory=dict)
    job_options: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_scheduler_payload(cls, value: Any):
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        normalized["queue_name"] = normalized.get("queue_name") or normalized.get("queue")
        normalized["func_path"] = normalized.get("func_path") or normalized.get("func") or normalized.get("task")
        normalized["cron"] = normalized.get("cron") or None
        normalized["interval"] = None if normalized.get("interval") in ("", None) else normalized.get("interval")
        normalized["args"] = list(normalized.get("args") or [])
        normalized["kwargs"] = dict(normalized.get("kwargs") or {})
        normalized["job_options"] = dict(normalized.get("job_options") or {})
        normalized["meta"] = dict(normalized.get("meta") or {})
        return normalized

    @model_validator(mode="after")
    def validate_schedule_definition(self):
        has_cron = bool(self.cron)
        has_interval = self.interval is not None
        if has_cron == has_interval:
            raise ValueError("CronTaskSpec must provide exactly one of cron or interval")
        return self


class Task(TaranisBaseModel):
    """Task execution result model"""

    _core_endpoint = "/config/task-results"
    _model_name = "task"
    _pretty_name = "Task"
    _cache_timeout = 1

    id: str
    task: str | None = None
    result: Any | None = None
    status: str | None = None
    last_run: datetime | None = None
    last_success: datetime | None = None
