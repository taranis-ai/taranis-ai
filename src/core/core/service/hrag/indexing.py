"""PostgreSQL owns index records, leases, generation activation and stale-result checks."""

import hashlib
import json
from datetime import timedelta

from models.hrag import (
    HRAG_EXTRACTION_SCHEMA_VERSION,
    HRAG_SCHEMA_VERSION,
    EmbeddingSettings,
    IndexStatus,
    IndexSubmission,
    bounded_content,
    input_fingerprint,
    split_content,
)

from core.config import Config
from core.log import logger
from core.managers.db_manager import db
from core.model.hrag import HragGeneration, HragIndex
from core.model.news_item import NewsItem
from core.model.settings import Settings
from core.service.hrag.stores import graph_document_keys, project_graph, prune_graph, save_chunks


PIPELINES = ("embedding", "extraction")


def current_configuration(pipeline: str, settings: dict) -> dict | None:
    endpoint = Settings.get_llm_endpoint(pipeline, settings)
    if not endpoint or endpoint["processing_mode"] != "realtime":
        return None
    endpoint_id = settings.get(f"llm_{pipeline}_endpoint") or settings.get("llm_default_endpoint") or ""
    embedding_settings = EmbeddingSettings.model_validate(settings)
    limit = Config.HRAG_EXTRACTION_LIMIT if pipeline == "extraction" else embedding_settings.hrag_embedding_limit
    if not 1 <= limit <= 200_000:
        return None
    dimensions = 0
    if pipeline == "embedding":
        from core.service.endpoint_health import get_status

        dimensions = endpoint.get("dimensions") or get_status("llm", endpoint_id, settings["llm_endpoints"][endpoint_id]).get(
            "embedding_dimensions"
        )
        if dimensions is None:
            return None
    configuration = {
        "endpoint_id": endpoint_id,
        "base_url": endpoint["base_url"],
        "model": endpoint["model"],
        "api_format": endpoint["api_format"],
        "limit": limit,
        "schema": HRAG_EXTRACTION_SCHEMA_VERSION if pipeline == "extraction" else HRAG_SCHEMA_VERSION,
        "dimensions": dimensions,
    }
    if pipeline == "embedding":
        configuration["automatic_dimensions"] = endpoint.get("dimensions") is None
        configuration["chunking"] = {
            "enabled": embedding_settings.hrag_chunking_enabled,
            "size": embedding_settings.hrag_chunk_size,
            "overlap": embedding_settings.hrag_chunk_overlap,
        }
    if pipeline == "extraction":
        configuration["reasoning_effort"] = (
            None if settings["hrag_extraction_reasoning_effort"] == "default" else settings["hrag_extraction_reasoning_effort"]
        )
        configuration["verification"] = None
        if settings["hrag_relationship_verification_enabled"]:
            verifier = Settings.get_llm_endpoint("extraction_verification", settings)
            if not verifier or verifier["processing_mode"] != "realtime":
                return None
            configuration["verification"] = {
                "endpoint_id": settings.get("llm_extraction_verification_endpoint") or settings.get("llm_default_endpoint"),
                **{key: verifier[key] for key in ("base_url", "model", "api_format")},
            }
    return configuration


def generation_endpoint(generation: HragGeneration) -> dict | None:
    return _frozen_endpoint(generation.config, generation.pipeline)


def generation_verification_endpoint(generation: HragGeneration) -> dict | None:
    configuration = generation.config["verification"]
    return _frozen_endpoint(configuration, "extraction_verification") if configuration else None


def _frozen_endpoint(configuration: dict, feature: str) -> dict | None:
    from models.llm import LLMProvider

    provider = Settings.get_settings().get("llm_endpoints", {}).get(configuration["endpoint_id"])
    if not provider or not provider.get("enabled", True):
        return None
    normalized = LLMProvider.model_validate(provider)
    if not normalized.supports(feature):
        return None
    endpoint = normalized.for_feature(feature)
    if not endpoint or endpoint["processing_mode"] != "realtime":
        return None
    if feature == "embedding":
        endpoint["dimensions"] = None if configuration.get("automatic_dimensions") else configuration["dimensions"]
    # Freeze model and destination for this generation; rotate credentials independently.
    return {**endpoint, **{key: configuration[key] for key in ("base_url", "model", "api_format")}}


def fingerprint(item: NewsItem, generation: HragGeneration) -> str:
    return input_fingerprint(bounded_content(item.content, generation.config["limit"]), generation.id)


def reconcile() -> dict:
    if not Config.HRAG_ENABLED:
        return {"queued": 0}
    try:
        projected_keys = graph_document_keys()
    except Exception:
        projected_keys = None
        logger.exception("HRAG graph reconciliation unavailable")
    # Serialize generation creation and bounded scans across indexing passes.
    db.session.execute(db.select(Settings).with_for_update()).scalar_one()
    settings = Settings.get_settings()
    selected = []
    for pipeline in PIPELINES:
        config = current_configuration(pipeline, settings)
        if not config:
            continue
        generation_id = hashlib.sha256(json.dumps({"pipeline": pipeline, **config}, sort_keys=True).encode()).hexdigest()
        generation = db.session.get(HragGeneration, generation_id)
        if generation is None:
            active = db.session.scalar(db.select(HragGeneration.id).where(HragGeneration.pipeline == pipeline, HragGeneration.active))
            generation = HragGeneration.from_dict(
                {"id": generation_id, "pipeline": pipeline, "config": config, "active": not active, "cursor": "", "scanned": False}
            )
            db.session.add(generation)
            db.session.flush()
        selected.append(generation.id)
    generations = list(db.session.scalars(db.select(HragGeneration).where(db.or_(HragGeneration.id.in_(selected), HragGeneration.active))))
    generations = [
        generation
        for generation in generations
        if generation_endpoint(generation)
        and (generation.pipeline == "embedding" or generation.config["verification"] is None or generation_verification_endpoint(generation))
    ]
    for generation in generations:
        items = list(db.session.scalars(db.select(NewsItem).where(NewsItem.id > generation.cursor).order_by(NewsItem.id).limit(500)))
        for item in items:
            expected = fingerprint(item, generation)
            index_record = db.session.scalar(
                db.select(HragIndex).where(HragIndex.news_item_id == item.id, HragIndex.generation_id == generation.id)
            )
            if index_record is None:
                index_record = HragIndex.from_dict(
                    {"news_item_id": item.id, "generation_id": generation.id, "fingerprint": expected, "status": "pending"}
                )
                db.session.add(index_record)
            elif index_record.fingerprint != expected:
                index_record.fingerprint, index_record.status, index_record.result, index_record.token = expected, "pending", None, None
                index_record.attempts, index_record.retry_after, index_record.lease_until = 0, None, None
            index_record.truncated = len(item.content or "") > generation.config["limit"]
        generation.cursor = items[-1].id if len(items) == 500 else ""
        generation.scanned = generation.scanned or len(items) < 500
    if projected_keys is not None:
        for index_record in db.session.scalars(
            db.select(HragIndex)
            .join(HragGeneration)
            .where(HragGeneration.pipeline == "extraction", HragIndex.status == "ready", HragIndex.result.is_not(None))
        ):
            if index_record.graph_key not in projected_keys:
                index_record.status, index_record.token, index_record.lease_until = "pending", None, None
    now = HragIndex.utcnow()
    # Reissue lost Redis indexing jobs only after its PostgreSQL lease expires.
    job_ids = []
    for pipeline in PIPELINES:
        eligible = db.session.scalars(
            db.select(HragIndex)
            .where(
                HragIndex.generation_id.in_([g.id for g in generations if g.pipeline == pipeline]),
                HragIndex.status != "ready",
                db.or_(HragIndex.lease_until.is_(None), HragIndex.lease_until < now),
                db.or_(HragIndex.retry_after.is_(None), HragIndex.retry_after <= now),
            )
            .order_by(HragIndex.updated, HragIndex.id)
            .limit(50)
        )
        for index_record in eligible:
            index_record.status = "queued"
            index_record.token = None
            index_record.lease_until = now + timedelta(minutes=15)
            job_ids.append(("embeddings" if pipeline == "embedding" else "hrag", index_record.id))
    db.session.commit()
    from core.managers.queue_manager import queue_manager

    queued = 0
    for queue, index_id in job_ids:
        if queue_manager.enqueue_task(queue, "hrag_index", index_id=index_id, job_timeout=720, result_ttl=0):
            queued += 1
        else:
            index_record = db.session.get(HragIndex, index_id)
            if index_record and index_record.status == "queued":
                index_record.lease_until = None
                db.session.commit()
    # Pruning is best effort. Authorization never depends on projection cleanup.
    try:
        keys = [
            index_record.graph_key
            for index_record in db.session.scalars(
                db.select(HragIndex).join(HragGeneration).where(HragGeneration.pipeline == "extraction", HragIndex.result.is_not(None))
            )
        ]
        db.session.rollback()
        prune_graph(keys)
    except Exception:
        logger.exception("HRAG graph cleanup failed")
    return {"queued": queued}


def claim(index_id: str) -> dict | None:
    if not Config.HRAG_ENABLED:
        return None
    index_record = db.session.scalar(db.select(HragIndex).where(HragIndex.id == index_id).with_for_update())
    if index_record is None or index_record.status == "ready":
        return None
    if index_record.status == "running" and index_record.lease_until and index_record.lease_until > HragIndex.utcnow():
        return None
    generation = db.session.get(HragGeneration, index_record.generation_id)
    item = db.session.get(NewsItem, index_record.news_item_id)
    if not generation or not item or not (endpoint := generation_endpoint(generation)):
        return None
    verification_endpoint = generation_verification_endpoint(generation) if generation.pipeline == "extraction" else None
    if generation.pipeline == "extraction" and generation.config["verification"] is not None and verification_endpoint is None:
        return None
    expected = fingerprint(item, generation)
    if expected != index_record.fingerprint:
        index_record.fingerprint, index_record.result, index_record.attempts = expected, None, 0
    content = bounded_content(item.content, generation.config["limit"])
    index_record.truncated = len(item.content or "") > generation.config["limit"]
    if not content.strip():
        index_record.status, index_record.result, index_record.lease_until = "ready", None, None
        db.session.commit()
        return None
    index_record.status, index_record.token = "running", HragIndex.uuid7_str()
    index_record.lease_until = HragIndex.utcnow() + timedelta(minutes=15)
    index_record.attempts += 1
    payload = {
        "id": index_record.id,
        "token": index_record.token,
        "fingerprint": index_record.fingerprint,
        "pipeline": generation.pipeline,
        "content": content,
        "endpoint": endpoint,
        "verification_endpoint": verification_endpoint,
        "reasoning_effort": generation.config.get("reasoning_effort"),
        "dimensions": generation.config["dimensions"],
        "cached_result": index_record.result,
        "chunks": [chunk.model_dump() for chunk in split_content(content, **generation.config["chunking"])]
        if generation.pipeline == "embedding"
        else [],
    }
    db.session.commit()
    return payload


def submit(index_id: str, submission: IndexSubmission) -> tuple[dict, int]:
    index_record = db.session.scalar(db.select(HragIndex).where(HragIndex.id == index_id).with_for_update())
    if not Config.HRAG_ENABLED or index_record is None:
        return {"error": "HRAG index unavailable"}, 404
    if index_record.token != submission.token or index_record.fingerprint != submission.fingerprint:
        return {"error": "Stale HRAG result"}, 409
    generation = db.session.get(HragGeneration, index_record.generation_id)
    item = db.session.scalar(db.select(NewsItem).where(NewsItem.id == index_record.news_item_id).with_for_update())
    if item is None or generation is None or fingerprint(item, generation) != index_record.fingerprint:
        return {"error": "Stale HRAG result"}, 409
    if index_record.status == "ready":
        return {"message": "HRAG result already accepted"}, 200
    if submission.failed:
        index_record.status = "pending"
        index_record.retry_after = HragIndex.utcnow() + timedelta(seconds=min(3600, 30 * 2 ** min(index_record.attempts, 7)))
        index_record.lease_until = None
        index_record.updated = HragIndex.utcnow()
        db.session.commit()
        return {"message": "HRAG retry scheduled"}, 200
    content = bounded_content(item.content, generation.config["limit"])
    if generation.pipeline == "extraction":
        if submission.extraction is None or submission.chunks is not None:
            return {"error": "Expected extraction result"}, 400
        try:
            result = submission.extraction.validate_content(content)
        except ValueError:
            return {"error": "Invalid evidence passages"}, 400
        index_record.result = result.model_dump()
        # Freeze identifiers before commit expires ORM state; a concurrent edit
        # must never label an old result with a newly assigned fingerprint.
        projection = (index_record.id, index_record.fingerprint, item.id, generation.id)
        db.session.commit()
        project_graph(*projection, result)
    else:
        if submission.extraction is not None:
            return {"error": "Expected embedding result"}, 400
        expected = split_content(content, **generation.config["chunking"])
        chunks = submission.chunks
        if chunks is None or len(chunks) != len(expected):
            return {"error": "Expected chunk embeddings"}, 400
        if any((chunk.start, chunk.end) != (span.start, span.end) for chunk, span in zip(chunks, expected, strict=True)):
            return {"error": "Invalid chunk offsets"}, 400
        if any(len(chunk.embedding) != generation.config["dimensions"] for chunk in chunks):
            return {"error": "Unexpected embedding dimensions"}, 400
        save_chunks(index_record.id, chunks)
        index_record.result = None
    # Content can change while Neo4j is updated. Never reactivate a stale submission.
    db.session.flush()
    db.session.expire_all()
    index_record = db.session.scalar(db.select(HragIndex).where(HragIndex.id == index_id).with_for_update())
    if index_record is None or index_record.token != submission.token or index_record.fingerprint != submission.fingerprint:
        db.session.rollback()
        return {"error": "Stale HRAG result"}, 409
    item = db.session.get(NewsItem, index_record.news_item_id)
    if item is None or fingerprint(item, generation) != index_record.fingerprint:
        db.session.rollback()
        return {"error": "Stale HRAG result"}, 409
    index_record.status, index_record.lease_until, index_record.retry_after = "ready", None, None
    index_record.updated = HragIndex.utcnow()
    db.session.commit()
    return {"message": "HRAG result accepted"}, 200


def index_status(news_item_ids: list[str] | None = None) -> dict:
    generations = []
    for generation in db.session.scalars(db.select(HragGeneration).order_by(HragGeneration.created)):
        chunking = generation.config["chunking"] if generation.pipeline == "embedding" else None
        query = db.select(HragIndex.status, db.func.count()).where(HragIndex.generation_id == generation.id)
        if news_item_ids:
            query = query.where(HragIndex.news_item_id.in_(news_item_ids))
        counts = dict(db.session.execute(query.group_by(HragIndex.status)).all())
        generations.append(
            {
                "id": generation.id,
                "pipeline": generation.pipeline,
                "active": generation.active,
                "model": generation.config["model"],
                "scanned": generation.scanned,
                "counts": counts,
                "chunk_size": chunking["size"] if chunking else None,
                "chunk_overlap": chunking["overlap"] if chunking else None,
                "chunking_enabled": chunking["enabled"] if chunking else None,
                "content_limit": generation.config["limit"],
            }
        )
    errors = []
    settings = Settings.get_settings()
    if Config.HRAG_ENABLED and current_configuration("extraction", settings) is None:
        errors.append(
            "Assign compatible realtime extraction and Decisions verification endpoints, or disable relationship verification."
            if settings["hrag_relationship_verification_enabled"]
            else "Assign a compatible realtime HRAG extraction endpoint in LLM Endpoints."
        )
    if Config.HRAG_ENABLED and current_configuration("embedding", settings) is None:
        errors.append("Assign an embedding endpoint and wait for its dimension check to complete. Save the endpoint to run the check again.")
    return IndexStatus(enabled=Config.HRAG_ENABLED, generations=generations, configuration_errors=errors).model_dump()


def activate(generation_id: str) -> tuple[dict, int]:
    db.session.execute(db.select(Settings).with_for_update()).scalar_one()
    generation = db.session.get(HragGeneration, generation_id)
    if not generation or not generation.scanned:
        return {"error": "Generation backfill is incomplete"}, 409
    for item in db.session.scalars(db.select(NewsItem)):
        index_record = db.session.scalar(
            db.select(HragIndex).where(HragIndex.news_item_id == item.id, HragIndex.generation_id == generation.id)
        )
        if not index_record or index_record.status != "ready" or index_record.fingerprint != fingerprint(item, generation):
            return {"error": "Generation backfill is incomplete"}, 409
    db.session.execute(db.update(HragGeneration).where(HragGeneration.pipeline == generation.pipeline).values(active=False))
    generation.active = True
    db.session.commit()
    return {"message": "HRAG generation activated"}, 200


def reprocess(generation_id: str) -> tuple[dict, int]:
    generation = db.session.get(HragGeneration, generation_id)
    if not generation:
        return {"error": "Generation not found"}, 404
    generation.cursor, generation.scanned = "", False
    db.session.execute(
        db.update(HragIndex)
        .where(HragIndex.generation_id == generation_id)
        .values(status="pending", token=None, result=None, lease_until=None, retry_after=None, attempts=0)
    )
    db.session.commit()
    return {"message": "HRAG reprocessing scheduled"}, 200
