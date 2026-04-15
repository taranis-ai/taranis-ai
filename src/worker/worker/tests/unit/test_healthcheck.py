import pytest

import worker.healthcheck as healthcheck


class FakeRedis:
    def __init__(
        self,
        *,
        worker_keys: list[str] | None = None,
        leader: str | None = None,
    ):
        self.worker_keys = worker_keys or []
        self.leader = leader
        self.ping_called = False
        self.scan_match: str | None = None

    def ping(self):
        self.ping_called = True
        return True

    def scan_iter(self, *, match: str, count: int):
        self.scan_match = match
        assert count == 1
        for key in self.worker_keys:
            if key.startswith(match[:-1]):
                yield key

    def get(self, key: str):
        assert key == healthcheck.CRON_LEADER_KEY
        return self.leader


def test_check_worker_health_passes_when_local_worker_key_exists():
    redis_connection = FakeRedis(worker_keys=["rq:worker:node-a.12345"])

    healthcheck.check_worker_health(redis_connection=redis_connection, hostname="node-a")

    assert redis_connection.ping_called is True
    assert redis_connection.scan_match == "rq:worker:node-a.*"


def test_check_worker_health_fails_when_local_worker_key_missing():
    redis_connection = FakeRedis(worker_keys=["rq:worker:node-b.99999"])

    with pytest.raises(RuntimeError, match="no worker key found"):
        healthcheck.check_worker_health(redis_connection=redis_connection, hostname="node-a")


def test_check_cron_health_passes_with_leader():
    redis_connection = FakeRedis(leader="cron-b-1")

    healthcheck.check_cron_health(redis_connection)

    assert redis_connection.ping_called is True


def test_check_cron_health_fails_without_leader():
    with pytest.raises(RuntimeError, match="leader lock is missing"):
        healthcheck.check_cron_health(FakeRedis(leader=None))
