"""RQ execution only; durable work and authorization remain in core."""

import asyncio

from llm_bot.tasks.evidence import prepare_evidence_extraction
from llm_bot.tasks.llm_utils import InvalidLLMOutputError
from models.hrag import CompactExtractionResult, EmbeddingResult, ExtractionResult, IndexJob, IndexSubmission, extraction_vocabulary

from worker.core_api import CoreApi
from worker.http_client import http_request, http_session_scope
from worker.llm import get_llm_client
from worker.log import logger
from worker.telemetry import instrument_job


@instrument_job
@http_session_scope()
def reconcile_index():
    if CoreApi().api_post("/worker/hrag/reconcile") is None:
        raise RuntimeError("HRAG reconciliation unavailable")


async def infer(job: IndexJob) -> dict:
    if job.cached_result is not None:
        return job.cached_result
    if job.pipeline == "embedding":
        response = http_request(
            "POST",
            f"{job.endpoint.base_url}/embeddings",
            json={"input": job.content, "model": job.endpoint.model, "dimensions": job.dimensions},
            headers={"Authorization": f"Bearer {job.endpoint.api_key}"} if job.endpoint.api_key else {},
            timeout=job.endpoint.timeout,
            verify=True,
        )
        response.raise_for_status()
        result = EmbeddingResult(embedding=response.json()["data"][0]["embedding"])
        if len(result.embedding) != job.dimensions:
            raise ValueError("Unexpected embedding dimensions")
        return result.model_dump()
    if not job.content:
        return ExtractionResult().model_dump()

    def validate(result: CompactExtractionResult) -> CompactExtractionResult:
        try:
            result.resolve(job.content)
            return result
        except ValueError as exc:
            raise InvalidLLMOutputError("Evidence does not match source content") from exc

    task = prepare_evidence_extraction(job.content, extraction_vocabulary(), CompactExtractionResult, validate=validate)
    client = get_llm_client({"llm_endpoint": job.endpoint.model_dump()})
    return (await task.run(client)).resolve(job.content).model_dump()


@instrument_job
@http_session_scope()
def index_item(work_id: str):
    core = CoreApi()
    route = f"/worker/hrag/work/{work_id}"
    payload = core.api_post(route)
    if payload is None:
        raise RuntimeError("HRAG work unavailable")
    if payload.get("skip"):
        return
    job = IndexJob.model_validate(payload)
    submission = IndexSubmission(token=job.token, fingerprint=job.fingerprint)
    try:
        result = asyncio.run(infer(job))
        if job.pipeline == "embedding":
            submission.vector = EmbeddingResult.model_validate(result)
        else:
            submission.extraction = ExtractionResult.model_validate(result)
        if core.api_put(route, submission.model_dump(mode="json")) is None:
            raise RuntimeError("HRAG submission unavailable")
    except Exception:
        logger.exception("HRAG indexing failed")
        # A lost callback is recovered by the PostgreSQL lease and periodic reconciliation.
        core.api_put(route, IndexSubmission(token=job.token, fingerprint=job.fingerprint, failed=True).model_dump())
        raise RuntimeError("HRAG indexing failed; retry scheduled") from None
