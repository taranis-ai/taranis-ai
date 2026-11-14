"""PostgreSQL owns work, leases, generation activation and stale-result checks."""

import hashlib
import json
from datetime import timedelta

from models.hrag import HRAG_SCHEMA_VERSION, EmbeddingResult, IndexStatus, IndexSubmission, bounded_content, input_fingerprint

from core.config import Config
from core.log import logger
from core.managers.db_manager import db
from core.model.hrag import HragGeneration, HragWork
from core.model.news_item import NewsItem
from core.model.settings import Settings
from core.service.hrag.stores import graph_document_keys, project_graph, prune_graph, save_vector


PIPELINES = ("extraction", "embedding")


def current_configuration(pipeline: str, settings: dict) -> dict | None:
    endpoint = Settings.get_llm_endpoint(pipeline, settings)
    if not endpoint or endpoint["processing_mode"] != "realtime":
        return None
    endpoint_id = settings.get(f"llm_{pipeline}_endpoint") or settings.get("llm_default_endpoint")
    limit = Config.HRAG_EXTRACTION_LIMIT if pipeline == "extraction" else Config.HRAG_EMBEDDING_LIMIT
    if not 1 <= limit <= 200_000 or not 1 <= Config.HRAG_EMBEDDING_DIMENSIONS <= 16000:
        return None
    return {
        "endpoint_id": endpoint_id,
        "base_url": endpoint["base_url"],
        "model": endpoint["model"],
        "api_format": endpoint["api_format"],
        "limit": limit,
        "schema": HRAG_SCHEMA_VERSION,
        "dimensions": Config.HRAG_EMBEDDING_DIMENSIONS if pipeline == "embedding" else 0,
    }


def generation_endpoint(generation: HragGeneration) -> dict | None:
    from models.llm import LLMProvider

    provider = Settings.get_settings().get("llm_endpoints", {}).get(generation.config["endpoint_id"])
    if not provider or not provider.get("enabled", True):
        return None
    normalized = LLMProvider.model_validate(provider)
    if not normalized.supports(generation.pipeline):
        return None
    endpoint = normalized.for_feature(generation.pipeline)
    if not endpoint or endpoint["processing_mode"] != "realtime":
        return None
    # Freeze model and destination for this generation; rotate credentials independently.
    return {**endpoint, **{key: generation.config[key] for key in ("base_url", "model", "api_format")}}


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
    # Serialize generation creation and bounded scans across cron/startup requests.
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
    for generation in generations:
        items = list(db.session.scalars(db.select(NewsItem).where(NewsItem.id > generation.cursor).order_by(NewsItem.id).limit(500)))
        for item in items:
            expected = fingerprint(item, generation)
            work = db.session.scalar(db.select(HragWork).where(HragWork.news_item_id == item.id, HragWork.generation_id == generation.id))
            if work is None:
                work = HragWork.from_dict(
                    {"news_item_id": item.id, "generation_id": generation.id, "fingerprint": expected, "status": "pending"}
                )
                db.session.add(work)
            elif work.fingerprint != expected:
                work.fingerprint, work.status, work.result, work.token = expected, "pending", None, None
                work.attempts, work.retry_after, work.lease_until = 0, None, None
            work.truncated = len(item.content or "") > generation.config["limit"]
        generation.cursor = items[-1].id if len(items) == 500 else ""
        generation.scanned = generation.scanned or len(items) < 500
    if projected_keys is not None:
        for work in db.session.scalars(
            db.select(HragWork)
            .join(HragGeneration)
            .where(HragGeneration.pipeline == "extraction", HragWork.status == "ready", HragWork.result.is_not(None))
        ):
            if work.graph_key not in projected_keys:
                work.status, work.token, work.lease_until = "pending", None, None
    now = HragWork.utcnow()
    # Reissue lost Redis work only after its PostgreSQL lease expires.
    eligible = list(
        db.session.scalars(
            db.select(HragWork)
            .where(
                HragWork.generation_id.in_([g.id for g in generations]),
                HragWork.status != "ready",
                db.or_(HragWork.lease_until.is_(None), HragWork.lease_until < now),
                db.or_(HragWork.retry_after.is_(None), HragWork.retry_after <= now),
            )
            .order_by(HragWork.updated, HragWork.id)
            .limit(50)
        )
    )
    job_ids = []
    for work in eligible:
        work.status = "queued"
        work.token = None
        work.lease_until = now + timedelta(minutes=15)
        job_ids.append(work.id)
    db.session.commit()
    from core.managers.queue_manager import queue_manager

    queued = 0
    for work_id in job_ids:
        if queue_manager.enqueue_task("misc", "hrag_index", work_id=work_id, job_timeout=720, result_ttl=0):
            queued += 1
        else:
            work = db.session.get(HragWork, work_id)
            if work and work.status == "queued":
                work.lease_until = None
                db.session.commit()
    # Pruning is best effort. Authorization never depends on projection cleanup.
    try:
        keys = [
            work.graph_key
            for work in db.session.scalars(
                db.select(HragWork).join(HragGeneration).where(HragGeneration.pipeline == "extraction", HragWork.result.is_not(None))
            )
        ]
        db.session.rollback()
        prune_graph(keys)
    except Exception:
        logger.exception("HRAG graph cleanup failed")
    return {"queued": queued}


def claim(work_id: str) -> dict | None:
    if not Config.HRAG_ENABLED:
        return None
    work = db.session.scalar(db.select(HragWork).where(HragWork.id == work_id).with_for_update())
    if work is None or work.status == "ready":
        return None
    if work.status == "running" and work.lease_until and work.lease_until > HragWork.utcnow():
        return None
    generation = db.session.get(HragGeneration, work.generation_id)
    item = db.session.get(NewsItem, work.news_item_id)
    if not generation or not item or not (endpoint := generation_endpoint(generation)):
        return None
    expected = fingerprint(item, generation)
    if expected != work.fingerprint:
        work.fingerprint, work.result, work.attempts = expected, None, 0
    content = bounded_content(item.content, generation.config["limit"])
    work.truncated = len(item.content or "") > generation.config["limit"]
    if not content.strip():
        work.status, work.result, work.lease_until = "ready", None, None
        db.session.commit()
        return None
    work.status, work.token = "running", HragWork.uuid7_str()
    work.lease_until = HragWork.utcnow() + timedelta(minutes=15)
    work.attempts += 1
    payload = {
        "id": work.id,
        "token": work.token,
        "fingerprint": work.fingerprint,
        "pipeline": generation.pipeline,
        "content": content,
        "endpoint": endpoint,
        "dimensions": generation.config["dimensions"],
        "cached_result": work.result,
    }
    db.session.commit()
    return payload


def submit(work_id: str, submission: IndexSubmission) -> tuple[dict, int]:
    work = db.session.scalar(db.select(HragWork).where(HragWork.id == work_id).with_for_update())
    if not Config.HRAG_ENABLED or work is None:
        return {"error": "HRAG work unavailable"}, 404
    if work.token != submission.token or work.fingerprint != submission.fingerprint:
        return {"error": "Stale HRAG result"}, 409
    generation = db.session.get(HragGeneration, work.generation_id)
    item = db.session.scalar(db.select(NewsItem).where(NewsItem.id == work.news_item_id).with_for_update())
    if item is None or generation is None or fingerprint(item, generation) != work.fingerprint:
        return {"error": "Stale HRAG result"}, 409
    if work.status == "ready":
        return {"message": "HRAG result already accepted"}, 200
    if submission.failed:
        work.status = "pending"
        work.retry_after = HragWork.utcnow() + timedelta(seconds=min(3600, 30 * 2 ** min(work.attempts, 7)))
        work.lease_until = None
        work.updated = HragWork.utcnow()
        db.session.commit()
        return {"message": "HRAG retry scheduled"}, 200
    content = bounded_content(item.content, generation.config["limit"])
    if generation.pipeline == "extraction":
        if submission.extraction is None or submission.vector is not None:
            return {"error": "Expected extraction result"}, 400
        try:
            result = submission.extraction.validate_content(content)
        except ValueError:
            return {"error": "Invalid evidence passages"}, 400
        work.result = result.model_dump()
        # Freeze identifiers before commit expires ORM state; a concurrent edit
        # must never label an old result with a newly assigned fingerprint.
        projection = (work.id, work.fingerprint, item.id, generation.id)
        db.session.commit()
        project_graph(*projection, result)
    else:
        if submission.vector is None or submission.extraction is not None:
            return {"error": "Expected embedding result"}, 400
        result_vector = EmbeddingResult.model_validate(submission.vector)
        if len(result_vector.embedding) != generation.config["dimensions"]:
            return {"error": "Unexpected embedding dimensions"}, 400
        work.result = None  # The vector table is the single durable copy.
        save_vector(work.id, result_vector.embedding)
    # Content can change while Neo4j is updated. Never reactivate a stale submission.
    db.session.flush()
    db.session.expire_all()
    work = db.session.scalar(db.select(HragWork).where(HragWork.id == work_id).with_for_update())
    if work is None or work.token != submission.token or work.fingerprint != submission.fingerprint:
        db.session.rollback()
        return {"error": "Stale HRAG result"}, 409
    item = db.session.get(NewsItem, work.news_item_id)
    if item is None or fingerprint(item, generation) != work.fingerprint:
        db.session.rollback()
        return {"error": "Stale HRAG result"}, 409
    work.status, work.lease_until, work.retry_after = "ready", None, None
    work.updated = HragWork.utcnow()
    db.session.commit()
    return {"message": "HRAG result accepted"}, 200


def index_status(news_item_ids: list[str] | None = None) -> dict:
    generations = []
    for generation in db.session.scalars(db.select(HragGeneration).order_by(HragGeneration.created)):
        query = db.select(HragWork.status, db.func.count()).where(HragWork.generation_id == generation.id)
        if news_item_ids:
            query = query.where(HragWork.news_item_id.in_(news_item_ids))
        counts = dict(db.session.execute(query.group_by(HragWork.status)).all())
        generations.append(
            {
                "id": generation.id,
                "pipeline": generation.pipeline,
                "active": generation.active,
                "model": generation.config["model"],
                "scanned": generation.scanned,
                "counts": counts,
            }
        )
    return IndexStatus(enabled=Config.HRAG_ENABLED, generations=generations).model_dump()


def activate(generation_id: str) -> tuple[dict, int]:
    db.session.execute(db.select(Settings).with_for_update()).scalar_one()
    generation = db.session.get(HragGeneration, generation_id)
    if not generation or not generation.scanned:
        return {"error": "Generation backfill is incomplete"}, 409
    for item in db.session.scalars(db.select(NewsItem)):
        work = db.session.scalar(db.select(HragWork).where(HragWork.news_item_id == item.id, HragWork.generation_id == generation.id))
        if not work or work.status != "ready" or work.fingerprint != fingerprint(item, generation):
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
        db.update(HragWork)
        .where(HragWork.generation_id == generation_id)
        .values(status="pending", token=None, result=None, lease_until=None, retry_after=None, attempts=0)
    )
    db.session.commit()
    return {"message": "HRAG reprocessing scheduled"}, 200
