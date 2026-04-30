import os
from typing import Any

from models.task_submission_meta import TaskSubmissionMeta, is_task_submission_meta
from rq import SpawnWorker, Worker
from rq.job import Job

from worker.core_api import CoreApi
from worker.log import logger


def _get_signal_value(ret_val: int | None) -> int | None:
    if ret_val is None or not os.WIFSIGNALED(ret_val):
        return None
    return os.WTERMSIG(ret_val)


def _get_task_submission(job: Job) -> TaskSubmissionMeta | None:
    task_submission = job.meta.get("task_submission")
    if is_task_submission_meta(task_submission):
        return task_submission

    logger.warning(f"Skipping killed work-horse failure propagation for job {job.id}: invalid task_submission metadata")
    return None


def persist_work_horse_killed_failure(job: Job, retpid: int, ret_val: int, _rusage: Any) -> None:
    task_submission = _get_task_submission(job)
    if not task_submission:
        return

    result: dict[str, Any] = {
        "reason": "work_horse_killed",
        "retpid": retpid,
        "ret_val": ret_val,
    }
    if signal_value := _get_signal_value(ret_val):
        result["signal"] = signal_value

    CoreApi().save_task_result(
        job.id,
        task_submission["task"],
        result,
        "FAILURE",
        worker_id=task_submission["worker_id"],
        worker_type=task_submission["worker_type"],
    )


class ReportingWorker(Worker):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("work_horse_killed_handler", persist_work_horse_killed_failure)
        super().__init__(*args, **kwargs)


class ReportingSpawnWorker(SpawnWorker):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("work_horse_killed_handler", persist_work_horse_killed_failure)
        super().__init__(*args, **kwargs)
