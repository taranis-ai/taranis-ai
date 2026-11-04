"""Prepare SBOMs outside Core request processes; publish only bounded normalized batches."""

from models.sbom import SBOM_BATCH_SIZE, SbomComponentBatch, SbomFindingBatch
from models.sbom_parser import SbomValidationError, parse_sbom
from rq import get_current_job

from worker.core_api import CoreApi, build_failure_task_result, build_success_task_result
from worker.http_client import http_request, http_session_scope
from worker.log import logger
from worker.telemetry import instrument_job


def submit_prepared(endpoint: str, payload: dict) -> dict:
    result = CoreApi().api_post(endpoint, payload)
    if not result or result.get("status") == "FAILED":
        raise RuntimeError("SBOM preparation was not accepted")
    return result


@instrument_job
@http_session_scope()
def sbom_import_task(upload_id: str):
    api = CoreApi()
    endpoint = f"/worker/sbom-uploads/{upload_id}"
    job = get_current_job()
    try:
        with http_request(
            "GET", url=f"{api.api_url}{endpoint}", headers=api.get_request_headers(), verify=api.verify, timeout=api.timeout
        ) as response:
            response.raise_for_status()
            parsed = parse_sbom(response.content or b"")
        submit_prepared(f"{endpoint}/begin", parsed.summary.model_dump())
        for offset in range(0, len(parsed.components), SBOM_BATCH_SIZE):
            batch = SbomComponentBatch(offset=offset, items=parsed.components[offset : offset + SBOM_BATCH_SIZE])
            submit_prepared(f"{endpoint}/components", batch.model_dump(mode="json"))
        for offset in range(0, len(parsed.findings), SBOM_BATCH_SIZE):
            findings = SbomFindingBatch(offset=offset, items=parsed.findings[offset : offset + SBOM_BATCH_SIZE])
            submit_prepared(f"{endpoint}/findings", findings.model_dump(mode="json"))
        result = submit_prepared(f"{endpoint}/complete", {})
    except Exception as exc:
        logger.exception("SBOM preparation failed")
        message = (
            exc.public_message if isinstance(exc, SbomValidationError) else "Unable to prepare the SBOM. Upload the file again to retry."
        )
        try:
            api.api_post(f"{endpoint}/failure", {"public_message": message})
            if job:
                api.save_task_result(
                    job.id,
                    "sbom_import_task",
                    "FAILURE",
                    worker_id=upload_id,
                    worker_type="sbom_import_task",
                    result=build_failure_task_result(message, reason="sbom_preparation_failed", retryable=True),
                )
        except Exception:
            logger.exception("Unable to report failed SBOM preparation")
        raise RuntimeError("SBOM preparation failed") from None
    if job:
        api.save_task_result(
            job.id,
            "sbom_import_task",
            "SUCCESS",
            worker_id=upload_id,
            worker_type="sbom_import_task",
            result=build_success_task_result(default_message="SBOM preview ready", data=result),
        )
    return result
