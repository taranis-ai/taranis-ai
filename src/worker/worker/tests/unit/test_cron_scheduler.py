import json

import fakeredis
import pytest
from models.task import CronTaskSpec
from pydantic import ValidationError

from worker.cron_scheduler import DEFS_KEY, NEXT_KEY, _decode, _normalize_spec, _sync_next_index


def test_cron_task_spec_accepts_current_fields():
    spec = CronTaskSpec.model_validate(
        {
            "queue_name": "collectors",
            "func_path": "collector_task",
            "args": ["source-1", False],
            "kwargs": {"dry_run": True},
            "job_options": {"timeout": 30},
            "meta": {"name": "Collector: Source 1"},
        }
    )

    assert spec.queue_name == "collectors"
    assert spec.func_path == "collector_task"
    assert spec.args == ["source-1", False]
    assert spec.kwargs == {"dry_run": True}
    assert spec.job_options == {"timeout": 30}
    assert spec.meta == {"name": "Collector: Source 1"}


def test_cron_task_spec_accepts_legacy_fields():
    spec = CronTaskSpec.model_validate(
        {
            "queue": "bots",
            "task": "bot_task",
            "args": ["bot-1"],
        }
    )

    assert spec.queue_name == "bots"
    assert spec.func_path == "bot_task"
    assert spec.args == ["bot-1"]
    assert spec.kwargs == {}
    assert spec.job_options == {}
    assert spec.meta == {}


def test_cron_task_spec_rejects_missing_required_fields():
    with pytest.raises(ValidationError):
        CronTaskSpec.model_validate({"interval": 30})

    assert _normalize_spec({"interval": 30}) is None


def test_sync_next_index_adds_missing_and_removes_stale_ids():
    redis_conn = fakeredis.FakeRedis(decode_responses=False)
    base_ts = 1000.0

    redis_conn.hset(
        DEFS_KEY,
        "job_interval_30",
        json.dumps({"queue_name": "misc", "func_path": "cleanup_token_blacklist", "interval": 30}),
    )
    redis_conn.hset(
        DEFS_KEY,
        "job_interval_45",
        json.dumps({"queue_name": "misc", "func_path": "cleanup_token_blacklist", "interval": 45}),
    )
    redis_conn.zadd(NEXT_KEY, {"stale_job": 1111.0})

    specs = _sync_next_index(redis_conn, base_ts)

    assert set(specs.keys()) == {"job_interval_30", "job_interval_45"}
    assert redis_conn.zscore(NEXT_KEY, "stale_job") is None
    assert redis_conn.zscore(NEXT_KEY, "job_interval_30") == 1030.0
    assert redis_conn.zscore(NEXT_KEY, "job_interval_45") == 1045.0


def test_decode_rejects_awaitable_values():
    async def awaitable_value():
        return b"job-1"

    coroutine = awaitable_value()
    try:
        with pytest.raises(TypeError, match="requires a synchronous Redis client"):
            _decode(coroutine, "redis.get")
    finally:
        coroutine.close()
