from core.managers.queue_manager import QueueManager
from core.model.bot import Bot
from core.model.osint_source import OSINTSource


class _FakeRedis:
    def zrange(self, key, start, end):
        return ["scheduler"] if key == "rq:cron_schedulers" else []


def test_get_scheduled_jobs_includes_cleanup_cron(monkeypatch):
    monkeypatch.setattr(OSINTSource, "get_all_for_collector", classmethod(lambda cls: []))
    monkeypatch.setattr(Bot, "get_all_for_collector", classmethod(lambda cls: []))

    queue_manager = QueueManager.__new__(QueueManager)
    queue_manager.error = ""
    queue_manager._queues = {}
    queue_manager._redis = _FakeRedis()

    schedules, status = QueueManager.get_scheduled_jobs(queue_manager)

    assert status == 200
    items = schedules.get("items", [])
    cleanup_jobs = [job for job in items if job.get("id") == "cron_misc_cleanup_token_blacklist"]
    assert cleanup_jobs, "expected cleanup cron job to be listed"
    cleanup_job = cleanup_jobs[0]
    assert cleanup_job.get("queue") == "misc"
    assert cleanup_job.get("schedule") == "0 2 * * *"
    assert cleanup_job.get("type") == "cron"
