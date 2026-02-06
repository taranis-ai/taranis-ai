from datetime import datetime
from typing import Any

from models.base import TaranisBaseModel


class Task(TaranisBaseModel):
    """Task execution result model"""

    _core_endpoint = "/config/task-results"
    _model_name = "task"
    _pretty_name = "Task"
    _cache_timeout = 10

    id: str
    task: str | None = None
    result: Any | None = None
    status: str | None = None
    last_run: datetime | None = None
    last_success: datetime | None = None
