import json
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler

import fakeredis
import pytest
from rq import Queue, Retry, SimpleWorker, get_current_job
from rq.job import JobStatus

from worker.config import Config
from worker.task_events import TaskEventScheduler, TaskEventWorker, task_started


class InProcessTaskEventWorker(TaskEventWorker, SimpleWorker):
    pass


class TaskNoticeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.observed.append((payload, self.server.job.get_status()))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *_args):
        pass


@task_started
def task_with_outcome(outcome):
    if outcome == "failure":
        raise ValueError("private task detail")
    if outcome == "retry" and not get_current_job().number_of_retries:
        return Retry(max=1, interval=0)
    return "done"


@pytest.mark.parametrize("outcome", ["success", "failure", "retry"])
def test_rq_transitions_publish_after_state_is_visible(requests_mock, outcome):
    connection = fakeredis.FakeRedis()
    queue = Queue("task-events", connection=connection)
    job = queue.enqueue_at(
        datetime.now(UTC) - timedelta(seconds=1),
        task_with_outcome,
        outcome,
        meta={"user_id": "owner", "checkpoint": "private snapshot"},
    )
    observed = []

    def observe_change(request, _context):
        observed.append((request.json(), job.get_status()))
        return {"message": "Task views invalidated"}

    requests_mock.post(f"{Config.TARANIS_CORE_URL}/worker/tasks/changed", json=observe_change)
    scheduler = TaskEventScheduler([queue], connection=connection)
    scheduler._acquired_locks = {queue.name}
    scheduler.enqueue_scheduled_jobs()
    assert observed == [({"user_ids": ["owner"]}, JobStatus.QUEUED)]

    worker = InProcessTaskEventWorker([queue], connection=connection)
    worker.work(burst=True)

    owner_statuses = [status for payload, status in observed if payload["user_ids"]]
    expected = [JobStatus.QUEUED, JobStatus.STARTED]
    if outcome == "retry":
        expected += [JobStatus.QUEUED, JobStatus.STARTED]
    expected.append(JobStatus.FAILED if outcome == "failure" else JobStatus.FINISHED)
    assert owner_statuses == expected
    assert [payload for payload, _status in observed if not payload["user_ids"]] == [{"user_ids": []}, {"user_ids": []}]
    assert all(payload in ({"user_ids": []}, {"user_ids": ["owner"]}) for payload, _status in observed)


@pytest.fixture
def task_event_redis():
    """Use a disposable Redis server so spawned workhorses share the same state."""
    import shutil
    import subprocess
    import time

    from redis import Redis
    from redis.exceptions import ConnectionError

    if not shutil.which("docker"):
        pytest.skip("Docker is required for the spawned-worker integration test")
    container = subprocess.check_output(
        ["docker", "run", "--rm", "-d", "-p", "127.0.0.1::6379", "redis:8-alpine", "redis-server", "--save", "", "--appendonly", "no"],
        text=True,
    ).strip()
    try:
        port = subprocess.check_output(["docker", "port", container, "6379"], text=True).strip().rsplit(":", 1)[1]
        connection = Redis(host="127.0.0.1", port=int(port), protocol=2)
        for _ in range(50):
            try:
                connection.ping()
                break
            except ConnectionError:
                time.sleep(0.1)
        else:
            pytest.fail("The isolated Redis server did not become ready")
        try:
            yield connection
        finally:
            connection.close()
    finally:
        subprocess.run(["docker", "rm", "-f", container], check=True, capture_output=True)


def test_spawned_worker_publishes_started_and_finished_states(task_event_redis, monkeypatch):
    import os
    from http.server import ThreadingHTTPServer
    from pathlib import Path
    from threading import Thread

    from worker.task_events import TaskEventSpawnWorker

    monkeypatch.setenv("PYTHONPATH", os.pathsep.join((str(Path(__file__).parent.resolve()), os.environ.get("PYTHONPATH", ""))))
    queue = Queue("spawned-task-events", connection=task_event_redis)
    job = queue.enqueue_at(datetime.now(UTC) - timedelta(seconds=1), task_with_outcome, "success", meta={"user_id": "owner"})
    with ThreadingHTTPServer(("127.0.0.1", 0), TaskNoticeHandler) as server:
        server.job = job
        server.observed = []
        thread = Thread(target=server.serve_forever)
        thread.start()
        api_url = f"http://127.0.0.1:{server.server_port}"
        monkeypatch.setenv("TARANIS_CORE_URL", api_url)
        monkeypatch.setattr(Config, "TARANIS_CORE_URL", api_url)
        try:
            worker = TaskEventSpawnWorker([queue], connection=task_event_redis)
            worker.work(burst=True, with_scheduler=True)
            assert job.get_status() == JobStatus.FINISHED
            assert [status for payload, status in server.observed if payload["user_ids"]] == [
                JobStatus.QUEUED,
                JobStatus.STARTED,
                JobStatus.FINISHED,
            ]
            assert all(payload in ({"user_ids": []}, {"user_ids": ["owner"]}) for payload, _ in server.observed)
        finally:
            server.shutdown()
            thread.join()
