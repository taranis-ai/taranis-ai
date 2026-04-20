import pytest

import worker.healthcheck as healthcheck


class FakeRedis:
    def __init__(
        self,
        *,
        workers: dict[str, dict[str, str]] | None = None,
        leader: str | None = None,
    ):
        self.workers = workers or {}
        self.leader = leader
        self.ping_called = False
        self.scan_match: str | None = None
        self.hgetall_keys: list[str] = []

    def ping(self):
        self.ping_called = True
        return True

    def scan_iter(self, *, match: str, count: int):
        self.scan_match = match
        assert count > 0
        for key in self.workers:
            if key.startswith(match[:-1]):
                yield key

    def hgetall(self, key: str):
        self.hgetall_keys.append(key)
        return self.workers.get(key, {})

    def get(self, key: str):
        assert key == healthcheck.CRON_LEADER_KEY
        return self.leader


def test_check_worker_health_passes_when_expected_queue_exists(monkeypatch):
    monkeypatch.setattr(healthcheck.Config, "WORKER_TYPES", ["Collectors"])
    redis_connection = FakeRedis(workers={"rq:worker:worker-a": {"queues": "collectors"}})

    healthcheck.check_worker_health(redis_connection=redis_connection, hostname="node-a")

    assert redis_connection.ping_called is True
    assert redis_connection.scan_match == "rq:worker:*"
    assert redis_connection.hgetall_keys == ["rq:worker:worker-a"]


def test_check_worker_health_fails_when_expected_queue_missing(monkeypatch):
    monkeypatch.setattr(healthcheck.Config, "WORKER_TYPES", ["Collectors"])
    redis_connection = FakeRedis(workers={"rq:worker:worker-b": {"queues": "bots"}})

    with pytest.raises(RuntimeError, match="no active worker found for queues: collectors"):
        healthcheck.check_worker_health(redis_connection=redis_connection, hostname="node-a")


def test_check_cron_health_passes_with_leader():
    redis_connection = FakeRedis(leader="cron-b-1")

    healthcheck.check_cron_health(redis_connection)

    assert redis_connection.ping_called is True


def test_check_cron_health_fails_without_leader():
    with pytest.raises(RuntimeError, match="leader lock is missing"):
        healthcheck.check_cron_health(FakeRedis(leader=None))
