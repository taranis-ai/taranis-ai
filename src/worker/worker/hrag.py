"""RQ execution only; durable index records and authorization remain in core."""

import asyncio
from dataclasses import replace

from llm_bot.schemas import EntityRelationshipExtractionRequest
from llm_bot.tasks.entity_relationship_extraction import prepare_entity_relationship_extraction
from llm_bot.tasks.llm_utils import InvalidLLMOutputError
from models.hrag import (
    ChunkEmbedding,
    CompactExtractionResult,
    ExtractionResult,
    IndexJob,
    IndexSubmission,
    extraction_vocabulary,
    relationship_instructions,
)
from models.llm import EmbeddingDimensionMismatch

from worker.core_api import CoreApi
from worker.embedding import create_embeddings
from worker.hrag_verification import verify_extraction
from worker.http_client import http_session_scope
from worker.llm import get_decisions_client, get_llm_client
from worker.log import logger
from worker.telemetry import instrument_job


@instrument_job
@http_session_scope()
def reconcile_index(generation_id: str | None = None):
    payload = {"action": "reconcile", "generation_id": generation_id} if generation_id else None
    if CoreApi().api_post("/worker/hrag/reconcile", payload) is None:
        raise RuntimeError("HRAG reconciliation unavailable")


async def infer(job: IndexJob) -> dict:
    if job.cached_result is not None:
        return job.cached_result
    if job.pipeline == "embedding":
        chunks = []
        for offset in range(0, len(job.chunks), 32):
            batch = job.chunks[offset : offset + 32]
            vectors = create_embeddings([job.content[span.start : span.end] for span in batch], job.endpoint.model_dump(), job.dimensions)
            chunks.extend(
                ChunkEmbedding(**span.model_dump(), embedding=vector).model_dump() for span, vector in zip(batch, vectors, strict=True)
            )
        return {"chunks": chunks}
    if not job.content:
        return ExtractionResult().model_dump()

    def validate(result: CompactExtractionResult) -> CompactExtractionResult:
        try:
            result.resolve(job.content, quarantine_invalid_relations=True, profile=job.extraction_profile)
            return result
        except ValueError as exc:
            raise InvalidLLMOutputError("Evidence does not match source content") from exc

    request = EntityRelationshipExtractionRequest.model_validate(
        {"text": job.content, "schema": extraction_vocabulary(job.extraction_profile), "reasoning_effort": job.reasoning_effort}
    )
    task = prepare_entity_relationship_extraction(request, result_model=CompactExtractionResult, validate=validate)
    task = replace(task, system_input=task.system_input + "\n\n" + relationship_instructions(job.extraction_profile))
    client = get_llm_client({"llm_endpoint": job.endpoint.model_dump()}, reasoning_effort=job.reasoning_effort)
    proposals = await task.run(client)
    resolved = proposals.resolve(job.content, quarantine_invalid_relations=True, profile=job.extraction_profile)
    result = resolved
    if job.verification_endpoint is not None:
        verifier = get_decisions_client({"llm_endpoint": job.verification_endpoint.model_dump()})
        result = await verify_extraction(job.content, resolved, verifier)
    logger.info(
        f"HRAG extraction: verification={job.verification_endpoint is not None} quarantined={len(proposals.relations) - len(resolved.relations)} "
        f"rejected={len(resolved.relations) - len(result.relations)} accepted={len(result.relations)}"
    )
    return result.model_dump()


@instrument_job
@http_session_scope()
def index_item(index_id: str):
    core = CoreApi()
    route = f"/worker/hrag/index/{index_id}"
    payload = core.api_post(route)
    if payload is None:
        raise RuntimeError("HRAG index unavailable")
    if payload.get("skip"):
        return
    job = IndexJob.model_validate(payload)
    submission = IndexSubmission(token=job.token, fingerprint=job.fingerprint)
    try:
        result = asyncio.run(infer(job))
        if job.pipeline == "embedding":
            submission.chunks = [ChunkEmbedding.model_validate(chunk) for chunk in result["chunks"]]
        else:
            submission.extraction = ExtractionResult.model_validate(result)
        if core.api_put(route, submission.model_dump(mode="json")) is None:
            raise RuntimeError("HRAG submission unavailable")
    except Exception as exc:
        logger.exception("HRAG indexing failed")
        # A lost callback is recovered by the PostgreSQL lease and periodic reconciliation.
        core.api_put(route, IndexSubmission(token=job.token, fingerprint=job.fingerprint, failed=True).model_dump())
        message = "HRAG indexing failed; retry scheduled"
        if isinstance(exc, EmbeddingDimensionMismatch):
            message = EmbeddingDimensionMismatch.public_message
        raise RuntimeError(message) from None
