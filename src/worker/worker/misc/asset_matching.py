"""Run bounded historical scans through Core's authorization and persistence boundary."""

from rq import get_current_job

from worker.core_api import CoreApi, build_failure_task_result, build_success_task_result
from worker.http_client import http_session_scope
from worker.log import logger
from worker.telemetry import instrument_job


@instrument_job
@http_session_scope()
def asset_match_task(run_id: str):
    api = CoreApi()
    endpoint = f"/worker/asset-match-runs/{run_id}/batch"
    job = get_current_job()
    try:
        while True:
            result = api.api_post(endpoint, {})
            if not result or result.get("status") not in ("RUNNING", "COMPLETED"):
                raise RuntimeError("Asset intelligence scan failed")
            if result["status"] == "COMPLETED":
                if job:
                    api.save_task_result(
                        job.id,
                        "asset_match_task",
                        "SUCCESS",
                        worker_id=job.meta.get("worker_id"),
                        worker_type="asset_match_task",
                        result=build_success_task_result(default_message="Asset intelligence scan completed", data=result),
                    )
                return result
    except Exception:
        logger.exception("Asset intelligence scan failed")
        try:
            api.api_post(endpoint, {"failed": True})
            if job:
                api.save_task_result(
                    job.id,
                    "asset_match_task",
                    "FAILURE",
                    worker_id=job.meta.get("worker_id"),
                    worker_type="asset_match_task",
                    result=build_failure_task_result("Asset intelligence scan failed", reason="asset_scan_failed", retryable=True),
                )
        except Exception:
            logger.exception("Unable to report failed asset intelligence scan")
        raise RuntimeError("Asset intelligence scan failed") from None
