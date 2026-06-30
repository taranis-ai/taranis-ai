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
