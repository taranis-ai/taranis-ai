"""RQ execution only; durable work and authorization remain in core."""

import asyncio

from llm_bot.schemas import EntityRelationshipExtractionRequest
from llm_bot.tasks.entity_relationship_extraction import prepare_entity_relationship_extraction
from llm_bot.tasks.llm_utils import InvalidLLMOutputError
from models.hrag import (
    ChunkEmbedding,
    CompactExtractionResult,
    EmbeddingResult,
    ExtractionResult,
    IndexJob,
    IndexSubmission,
    extraction_vocabulary,
)

from worker.core_api import CoreApi
from worker.embedding import create_embedding, create_embeddings
from worker.hrag_verification import verify_extraction
from worker.http_client import http_session_scope
from worker.llm import get_decisions_client, get_llm_client
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
        if job.chunks:
            chunks = []
            for offset in range(0, len(job.chunks), 32):
                batch = job.chunks[offset : offset + 32]
                vectors = create_embeddings([job.content[span.start : span.end] for span in batch], job.endpoint.model_dump(), job.dimensions)
                chunks.extend(
                    ChunkEmbedding(**span.model_dump(), embedding=vector).model_dump() for span, vector in zip(batch, vectors, strict=True)
                )
            return {"chunks": chunks}
        vector = create_embedding(job.content, job.endpoint.model_dump(), job.dimensions)
        return EmbeddingResult(embedding=vector).model_dump()
    if not job.content:
        return ExtractionResult().model_dump()

    def validate(result: CompactExtractionResult) -> CompactExtractionResult:
        try:
            result.resolve(job.content, quarantine_invalid_relations=True)
            return result
        except ValueError as exc:
            raise InvalidLLMOutputError("Evidence does not match source content") from exc

    request = EntityRelationshipExtractionRequest.model_validate(
        {"text": job.content, "schema": extraction_vocabulary(), "reasoning_effort": job.reasoning_effort}
    )
    task = prepare_entity_relationship_extraction(request, result_model=CompactExtractionResult, validate=validate)
    client = get_llm_client({"llm_endpoint": job.endpoint.model_dump()}, reasoning_effort=job.reasoning_effort)
    proposals = await task.run(client)
    resolved = proposals.resolve(job.content, quarantine_invalid_relations=True)
    if job.verification_endpoint is None:
        raise RuntimeError("HRAG relationship verification is not configured")
    verifier = get_decisions_client({"llm_endpoint": job.verification_endpoint.model_dump()})
    result = await verify_extraction(job.content, resolved, verifier)
    logger.info(
        f"HRAG extraction: quarantined={len(proposals.relations) - len(resolved.relations)} "
        f"rejected={len(resolved.relations) - len(result.relations)} accepted={len(result.relations)}"
    )
    return result.model_dump()


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
            if job.chunks:
                submission.chunks = [ChunkEmbedding.model_validate(chunk) for chunk in result["chunks"]]
            else:
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
