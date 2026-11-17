"""Spawned-worker lifecycle check invoked inside the existing E2E worker service."""

import json
import os
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from uuid import uuid4

from rq import Queue
from rq.job import JobStatus

from worker import get_redis_connection
from worker.config import Config
from worker.task_events import TaskEventSpawnWorker, task_started


class TaskNoticeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.observed.append((payload, self.server.job.get_status()))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *_args):
        pass


@task_started
def spawned_task():
    return os.getpid()


def check_spawned_worker_notifications():
    with get_redis_connection(Config.REDIS_URL, Config.REDIS_PASSWORD) as connection:
        queue = Queue(f"spawned-task-events-{uuid4().hex}", connection=connection)
        job = queue.enqueue_at(
            datetime.now(UTC) - timedelta(seconds=1),
            spawned_task,
            meta={"user_id": "owner", "checkpoint": "private snapshot"},
            job_timeout=15,
        )
        try:
            with ThreadingHTTPServer(("127.0.0.1", 0), TaskNoticeHandler) as server:
                server.job = job
                server.observed = []
                thread = Thread(target=server.serve_forever)
                thread.start()
                # Both the parent and its fresh interpreter must use the observer.
                Config.TARANIS_CORE_URL = os.environ["TARANIS_CORE_URL"] = f"http://127.0.0.1:{server.server_port}"
                try:
                    worker = TaskEventSpawnWorker([queue], connection=connection)
                    worker.work(burst=True, with_scheduler=True)
                    assert job.get_status() == JobStatus.FINISHED
                    assert job.return_value() != os.getpid()
                    assert [status for payload, status in server.observed if payload["user_ids"]] == [
                        JobStatus.QUEUED,
                        JobStatus.STARTED,
                        JobStatus.FINISHED,
                    ]
                    assert all(payload in ({"user_ids": []}, {"user_ids": ["owner"]}) for payload, _ in server.observed)
                finally:
                    server.shutdown()
                    thread.join()
        finally:
            job.delete()
            queue.delete()
