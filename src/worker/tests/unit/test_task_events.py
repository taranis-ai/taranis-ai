from datetime import UTC, datetime, timedelta

import fakeredis
import pytest
from rq import Queue, Retry, SimpleWorker, get_current_job
from rq.job import JobStatus

from worker.config import Config
from worker.task_events import TaskEventScheduler, TaskEventWorker, task_started


class InProcessTaskEventWorker(TaskEventWorker, SimpleWorker):
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
