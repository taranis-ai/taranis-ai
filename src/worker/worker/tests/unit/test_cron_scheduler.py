import json

import fakeredis
import pytest
from models.task import CronTaskSpec
from models.task_submission_meta import build_worker_task_payload
from pydantic import ValidationError

import worker.cron_scheduler as cron_scheduler
from worker.cron_scheduler import DEFS_KEY, NEXT_KEY, _decode, _enqueue_due_job, _enqueue_key, _normalize_spec, _sync_next_index


def test_cron_task_spec_rejects_missing_required_fields():
    with pytest.raises(ValidationError):
        CronTaskSpec.model_validate({"interval": 30})

    assert _normalize_spec({"interval": 30}) is None


def test_cron_task_spec_rejects_missing_schedule_definition():
    with pytest.raises(ValidationError, match="exactly one of cron or interval"):
        CronTaskSpec.model_validate({"queue_name": "misc", "func_path": "cleanup_token_blacklist"})

    assert _normalize_spec({"queue_name": "misc", "func_path": "cleanup_token_blacklist"}) is None


def test_cron_task_spec_rejects_multiple_schedule_definitions():
    payload = {
        "queue_name": "misc",
        "func_path": "cleanup_token_blacklist",
        "cron": "0 2 * * *",
        "interval": 300,
    }

    with pytest.raises(ValidationError, match="exactly one of cron or interval"):
        CronTaskSpec.model_validate(payload)

    assert _normalize_spec(payload) is None


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


def test_sync_next_index_skips_invalid_specs_without_crashing():
    redis_conn = fakeredis.FakeRedis(decode_responses=False)
    base_ts = 1000.0

    redis_conn.hset(
        DEFS_KEY,
        "job_interval_30",
        json.dumps({"queue_name": "misc", "func_path": "cleanup_token_blacklist", "interval": 30}),
    )
    redis_conn.hset(
        DEFS_KEY,
        "job_invalid",
        json.dumps({"queue_name": "misc", "func_path": "cleanup_token_blacklist"}),
    )

    specs = _sync_next_index(redis_conn, base_ts)

    assert set(specs.keys()) == {"job_interval_30"}
    assert redis_conn.zscore(NEXT_KEY, "job_interval_30") == 1030.0
    assert redis_conn.zscore(NEXT_KEY, "job_invalid") is None


def test_decode_rejects_awaitable_values():
    async def awaitable_value():
        return b"job-1"

    coroutine = awaitable_value()
    try:
        with pytest.raises(TypeError, match="requires a synchronous Redis client"):
            _decode(coroutine, "redis.get")
    finally:
        coroutine.close()


def test_enqueue_due_job_updates_next_run_and_notifies_wait_key(monkeypatch, fake_queue):
    redis_conn = fakeredis.FakeRedis(decode_responses=False)
    monkeypatch.setattr(cron_scheduler, "Queue", fake_queue)

    rq_job_id = _enqueue_due_job(
        redis_conn,
        {},
        "osint_source_source-1",
        {
            "queue_name": "collectors",
            "func_path": "collector_task",
            "cron": "*/5 * * * *",
            "args": [build_worker_task_payload("collector_task", "source-1", fields={"manual": False})],
            "meta": {"name": "Collector: Source 1"},
        },
        now_ts=1000.0,
    )

    assert rq_job_id == "cron_osint_source_source-1_1000"
    assert fake_queue.enqueued_calls == [
        {
            "task": "worker.collectors.collector_tasks.collector_task",
            "args": (build_worker_task_payload("collector_task", "source-1", fields={"manual": False}),),
            "job_id": "cron_osint_source_source-1_1000",
            "kwargs": {
                "kwargs": {},
                "meta": {
                    "name": "Collector: Source 1",
                    "task_submission": {
                        "task": "collector_task",
                        "worker_id": "source-1",
                        "worker_type": "collector_task",
                    },
                },
            },
        }
    ]
    assert redis_conn.zscore(NEXT_KEY, "osint_source_source-1") is not None

    wait_key_result = redis_conn.blpop(_enqueue_key("osint_source_source-1"), timeout=1)
    assert wait_key_result is not None
    assert wait_key_result[1] == b"cron_osint_source_source-1_1000"  # type: ignore[comparison-with-callable]
