"""Validation and serialization for Redis-backed scheduler lists."""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, Json, PositiveInt, StrictStr, ValidationError, field_validator, model_serializer
from pydantic_core import PydanticUseDefault


class JobFilter(BaseModel):
    page: PositiveInt = 1
    limit: PositiveInt = 20
    search: str | None = None
    order: Annotated[
        str,
        Field(pattern=r"^(id|name|queue|type|schedule|next_run_time|last_run|started_at|failed_at|status)_(asc|desc)$"),
    ] = ""

    @field_validator("page", "limit", "order", mode="wrap")
    @classmethod
    def use_default_on_invalid(cls, value, handler):
        try:
            return handler(value)
        except ValidationError:
            raise PydanticUseDefault from None

    def paginate(self, jobs: list[dict[str, Any]], *, default_order: str) -> dict[str, Any]:
        if search := (self.search or "").strip().lower():
            jobs = [
                job
                for job in jobs
                if any(
                    search in str(job.get(field) or "").lower() for field in ("id", "name", "queue", "type", "schedule", "status", "error")
                )
            ]
        field, direction = (self.order or default_order).rsplit("_", 1)
        jobs = sorted(jobs, key=lambda job: str(job.get(field) or "").lower(), reverse=direction == "desc")
        jobs.sort(key=lambda job: job.get(field) is None)
        offset = (self.page - 1) * self.limit
        return {"items": jobs[offset : offset + self.limit], "total_count": len(jobs)}


class ScheduledJob(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    name: str = ""
    queue: str | None = None
    type: Literal["cron", "scheduled"]
    schedule: str | None = None
    last_run: datetime | None = None
    last_success: datetime | None = None
    next_run_time: datetime | None = None
    previous_run_time: datetime | None = None

    @field_validator("last_run", "last_success", "next_run_time", "previous_run_time")
    @classmethod
    def normalize_utc(cls, value: datetime | None) -> datetime | None:
        if value is None or value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    @model_serializer(mode="wrap")
    def serialize(self, handler, info):
        data = handler(self)
        now = (info.context or {}).get("now", datetime.now(UTC).replace(tzinfo=None))
        for name, value in (("last_run", self.last_run), ("next_run", self.next_run_time)):
            data[f"{name}_display"] = value.strftime("%Y-%m-%d %H:%M:%S UTC") if value else None
            relative = None
            if value:
                seconds = int((value - now).total_seconds())
                duration = abs(seconds)
                units = ((86400, "d", 3600, "h"), (3600, "h", 60, "m"), (60, "m", 1, "s"))
                label = f"{duration}s"
                for size, unit, remainder_size, remainder_unit in units:
                    if duration >= size:
                        count, remainder = divmod(duration, size)
                        remainder //= remainder_size
                        label = f"{count}{unit}" + (f" {remainder}{remainder_unit}" if remainder else "")
                        break
                relative = "now" if seconds == 0 else f"in {label}" if seconds > 0 else f"{label} ago"
            data[f"{name}_relative"] = relative

        badge = {"variant": "ghost", "label": "Queued" if self.type == "scheduled" else "Pending"}
        if self.type == "cron":
            if self.last_run is None:
                badge["label"] = "Pending first run"
            elif self.previous_run_time is None or self.last_run >= self.previous_run_time:
                badge = {"variant": "success", "label": "On schedule"}
        data.update(status_badge=badge, is_overdue=False)
        return data


class SchedulerTaskResult(BaseModel):
    reason: StrictStr | None = None


class StoredTaskResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    result: Json[SchedulerTaskResult] = Field(default_factory=SchedulerTaskResult)

    @field_validator("result", mode="wrap")
    @classmethod
    def ignore_malformed_result(cls, value, handler):
        try:
            return handler(value)
        except ValidationError:
            raise PydanticUseDefault from None
