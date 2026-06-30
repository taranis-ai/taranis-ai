from flask import Flask

from core.managers.queue_manager import QueueManager


def test_queue_manager_initializes_queues_with_configured_default_timeout(monkeypatch):
    queue_calls: list[dict[str, object]] = []

    class FakeRedis:
        def ping(self):
            return True

    class FakeQueue:
        def __init__(self, name, connection=None, default_timeout=None, **kwargs):
            queue_calls.append(
                {
                    "name": name,
                    "connection": connection,
                    "default_timeout": default_timeout,
                }
            )

    redis_conn = FakeRedis()

    monkeypatch.setattr("core.managers.queue_manager.Redis.from_url", lambda *args, **kwargs: redis_conn)
    monkeypatch.setattr("core.managers.queue_manager.Queue", FakeQueue)
    monkeypatch.setattr("core.managers.queue_manager.Config.REDIS_PASSWORD", None)
    monkeypatch.setattr("core.managers.queue_manager.Config.RQ_DEFAULT_JOB_TIMEOUT", 900)

    app = Flask(__name__)
    queue_manager = QueueManager(app)

    assert queue_manager.error == ""
    assert [call["name"] for call in queue_calls] == queue_manager.queue_names
    assert all(call["connection"] is redis_conn for call in queue_calls)
    assert all(call["default_timeout"] == 900 for call in queue_calls)
