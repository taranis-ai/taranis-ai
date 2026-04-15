import json
from datetime import datetime
from typing import Any

from pydantic import AliasChoices, ConfigDict, Field, field_validator, model_validator

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

    _core_endpoint = "/tasks"
    _model_name = "task"
    _pretty_name = "Task"
    _cache_timeout = 1

    id: str
    task: str | None = None
    result: Any | None = None
    status: str | None = None
    last_run: datetime | None = None
    last_success: datetime | None = None


class TaskSubmission(TaranisBaseModel):
    _core_endpoint = "/tasks"
    _model_name = "task_submission"
    _pretty_name = "Task Submission"

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(min_length=1, validation_alias=AliasChoices("id", "task_id"), serialization_alias="id")
    task: str | None = None
    result: Any | None = None
    status: str = Field(min_length=1)
    traceback: str | None = None

    @field_validator("id", "status", mode="after")
    @classmethod
    def strip_required_fields(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field cannot be empty")
        return stripped

    @field_validator("task", mode="after")
    @classmethod
    def normalize_task_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("result")
    @classmethod
    def ensure_json_serializable_result(cls, value: Any) -> Any:
        try:
            json.dumps(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("result must be JSON serializable") from exc
        return value


class TaskHistoryEntry(TaranisBaseModel):
    id: str
    task: str | None = None
    result: Any | None = None
    status: str | None = None
    last_run: datetime | None = None
    last_success: datetime | None = None


class TaskHistoryStats(TaranisBaseModel):
    last_run: str | None = None
    last_success: str | None = None
    last_run_display: str | None = None
    last_success_display: str | None = None
    successes: int = 0
    failures: int = 0
    total: int = 0
    success_pct: int = 0
    status_badge: dict[str, str] | None = None


class TaskHistoryTotals(TaranisBaseModel):
    successes: int = 0
    failures: int = 0
    overall_success_rate: int = 0


class TaskHistoryResponse(TaranisBaseModel):
    _core_endpoint = "/tasks"
    _cache_timeout = 1
    _model_name = "task_history_response"
    _pretty_name = "Task History Response"

    items: list[TaskHistoryEntry] = Field(default_factory=list)
    total_count: int = 0
    task_stats: dict[str, TaskHistoryStats] = Field(default_factory=dict)
    totals: TaskHistoryTotals = Field(default_factory=TaskHistoryTotals)
