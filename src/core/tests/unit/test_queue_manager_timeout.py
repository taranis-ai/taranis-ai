from math import ceil

import pytest
from flask import Flask

from core.config import Config, Settings
from core.managers.queue_manager import QueueManager
from tests.unit.conftest import FakeRedis, fake_queue_factory


def _build_queue_manager(monkeypatch, queue_calls: list[dict[str, object]], timeout: int | None = None):
    redis_conn = FakeRedis()

    monkeypatch.setattr("core.managers.queue_manager.Redis.from_url", lambda *args, **kwargs: redis_conn)
    monkeypatch.setattr("core.managers.queue_manager.Queue", fake_queue_factory(queue_calls))
    monkeypatch.setattr("core.managers.queue_manager.Config.REDIS_PASSWORD", None)
    if timeout is not None:
        monkeypatch.setattr("core.managers.queue_manager.Config.RQ_DEFAULT_JOB_TIMEOUT", timeout)

    app = Flask(__name__)
    queue_manager = QueueManager(app)
    return queue_manager, redis_conn


def test_queue_manager_initializes_queues_with_configured_default_timeout(monkeypatch):
    queue_calls: list[dict[str, object]] = []
    queue_manager, redis_conn = _build_queue_manager(monkeypatch, queue_calls, timeout=900)

    assert queue_manager.error == ""
    assert [call["name"] for call in queue_calls] == queue_manager.queue_names
    assert all(call["connection"] is redis_conn for call in queue_calls)
    assert all(call["default_timeout"] == 900 for call in queue_calls)


def test_queue_manager_initializes_queues_with_default_timeout(monkeypatch):
    queue_calls: list[dict[str, object]] = []
    queue_manager, redis_conn = _build_queue_manager(monkeypatch, queue_calls)

    assert queue_manager.error == ""
    assert [call["name"] for call in queue_calls] == queue_manager.queue_names
    assert all(call["connection"] is redis_conn for call in queue_calls)
    assert all(call["default_timeout"] == Config.RQ_DEFAULT_JOB_TIMEOUT for call in queue_calls)


def test_core_settings_default_rq_timeout_is_180():
    assert Settings.model_fields["RQ_DEFAULT_JOB_TIMEOUT"].default == 180


@pytest.mark.parametrize("bot_id", [None, 7, "bad id!"])
def test_execute_bot_task_rejects_invalid_job_id_component(bot_id, monkeypatch):
    queue_manager, _ = _build_queue_manager(monkeypatch, [])

    assert queue_manager.execute_bot_task(bot_id) == ({"error": "Invalid bot_id"}, 400)


def test_post_collection_dag_uses_one_job_with_sum_of_execution_timeouts(app, session, monkeypatch):
    from core.model.bot import Bot

    with app.app_context():
        manager = app.extensions["rq"]
        bots, _ = Bot.get_collector_run_graph()
        first = bots[0]
        first.parameters = {**first.parameters, "EXECUTION_TIMEOUT": 25, "REFRESH_INTERVAL": "* * * * *"}
        session.commit()
        calls = []

        def capture_enqueue(*args, **kwargs):
            calls.append((args, kwargs))
            return True

        monkeypatch.setattr(manager, "enqueue_task", capture_enqueue)
        assert manager.post_collection_bots("source-1", user_id="user-1", story_ids=["story-1"])[1] == 200
        assert len(calls) == 1
        args, options = calls[0]
        assert args == ("bots", "bot_pipeline_task", [bot.id for bot in bots])
        assert options["filter"] == {"SOURCE": "source-1", "STORY_IDS": ["story-1"]}
        assert options["meta"]["user_id"] == "user-1"
        assert options["job_timeout"] == ceil(1.2 * (25 + (len(bots) - 1) * Config.RQ_DEFAULT_JOB_TIMEOUT))
        assert first.get_cron_spec().job_options["job_timeout"] == 25

        calls.clear()
        assert manager.schedule_bot_dependents(first.id, {"STORY_IDS": ["story-1"]}, user_id="user-1")[1] == 200
        assert len(calls) == 1
        assert calls[0][1]["filter"] == {"STORY_IDS": ["story-1"]}
        assert calls[0][1]["meta"]["user_id"] == "user-1"
