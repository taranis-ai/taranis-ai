import worker.__main__ as worker_main_module
import worker.cron_scheduler as cron_scheduler_module


def test_worker_main_calls_start_worker(monkeypatch):
    called = {"start_worker": False}

    def fake_start_worker():
        called["start_worker"] = True

    monkeypatch.setattr(worker_main_module, "start_worker", fake_start_worker)

    worker_main_module.main()

    assert called["start_worker"] is True


def test_cron_scheduler_main_uses_config(monkeypatch):
    captured_kwargs = {}

    def fake_run_scheduler(**kwargs):
        captured_kwargs.update(kwargs)

    monkeypatch.setattr(cron_scheduler_module, "run_scheduler", fake_run_scheduler)
    monkeypatch.setattr(cron_scheduler_module.Config, "REDIS_URL", "redis://redis:6379/9")
    monkeypatch.setattr(cron_scheduler_module.Config, "REDIS_PASSWORD", "supersecret")
    monkeypatch.setattr(cron_scheduler_module.Config, "CRON_POLL_INTERVAL_SECONDS", 42.0)
    monkeypatch.setenv("CRON_NODE_ID", "cron-node-test")

    cron_scheduler_module.main()

    assert captured_kwargs == {
        "redis_url": "redis://redis:6379/9",
        "node_id": "cron-node-test",
        "poll_interval_seconds": 42.0,
        "redis_password": "supersecret",
    }
