from datetime import timedelta
from unittest.mock import Mock

import pytest
from models.hrag import ChunkEmbedding, CompactExtractionResult, EvidenceReference, ExtractionResult, IndexJob, IndexSubmission

from core.config import Config
from core.managers.db_manager import db
from core.model.hrag import HragGeneration, HragIndex
from core.model.news_item_attribute import NewsItemAttribute
from core.model.settings import Settings
from core.service.hrag import indexing
from core.service.hrag.retrieval import evidence_from_reference
from tests.application.support.builders import build_news_item_payload, create_story


@pytest.fixture
def configured_index(db_persistent_session, monkeypatch):
    monkeypatch.setattr(Config, "HRAG_ENABLED", True)
    settings = Settings.with_defaults(
        {
            "llm_endpoints": {
                "extract": {
                    "name": "Extraction",
                    "base_url": "https://example.invalid/v1",
                    "api_formats": {"responses": {"model": "extract"}},
                    "enabled": True,
                },
                "embed": {
                    "name": "Embedding",
                    "base_url": "https://example.invalid/v1",
                    "api_formats": {"embeddings": {"model": "embed", "dimensions": 3}},
                    "enabled": True,
                },
                "verify": {
                    "name": "Verification",
                    "base_url": "https://example.invalid/v1",
                    "api_formats": {"systemone": {"model": "verify"}},
                    "enabled": True,
                },
            },
            "llm_extraction_endpoint": "extract",
            "llm_embedding_endpoint": "embed",
            "llm_extraction_verification_endpoint": "verify",
            "hrag_relationship_verification_enabled": True,
        }
    )
    monkeypatch.setattr(Settings, "get_settings", classmethod(lambda cls: settings))
    monkeypatch.setattr("core.managers.queue_manager.queue_manager.enqueue_task", Mock(return_value=True))
    monkeypatch.setattr(indexing, "prune_graph", Mock())
    monkeypatch.setattr(indexing, "project_graph", Mock())
    monkeypatch.setattr(indexing, "graph_document_keys", lambda: {w.graph_key for w in db.session.scalars(db.select(HragIndex))})
    yield settings
    db.session.rollback()
    db.session.execute(db.delete(HragGeneration))
    db.session.commit()


def test_durable_index_lifecycle_cutoffs_retries_and_generations(configured_index):
    story = create_story(news_items=[build_news_item_payload(content="a" * 10000 + "b" * 10000)])
    item = story.news_items[0]
    try:
        indexing.reconcile()
        from core.managers.queue_manager import queue_manager

        assert {call.args[0] for call in queue_manager.enqueue_task.call_args_list} == {"embeddings", "hrag"}
        indexes = {
            db.session.get(HragGeneration, w.generation_id).pipeline: w
            for w in db.session.scalars(db.select(HragIndex).where(HragIndex.news_item_id == item.id))
        }
        extraction, embedding = indexes["extraction"], indexes["embedding"]
        assert db.session.get(HragGeneration, extraction.generation_id).config["schema"] == "v7"
        assert db.session.get(HragGeneration, embedding.generation_id).config["schema"] == "v2"
        assert db.session.get(HragGeneration, embedding.generation_id).config["limit"] == 10000
        original = {kind: index_record.fingerprint for kind, index_record in indexes.items()}
        job = indexing.claim(extraction.id)
        assert job and indexing.claim(extraction.id) is None
        assert job["reasoning_effort"] == "low"
        assert job["extraction_profile"] == "cybersecurity"
        assert job["verification_endpoint"]["model"] == "verify"
        initial = CompactExtractionResult.model_validate({"entities": [{"id": "a", "name": "a", "type": "ORG"}]}).resolve(job["content"])
        result = IndexSubmission(token=job["token"], fingerprint=job["fingerprint"], extraction=initial)
        assert indexing.submit(extraction.id, result)[1] == 200
        assert indexing.submit(extraction.id, result)[1] == 200
        reference = EvidenceReference(citation="G1", index_id=extraction.id, fingerprint=extraction.fingerprint)
        authorized = {extraction.id: (extraction, db.session.get(HragGeneration, extraction.generation_id), item)}
        assert evidence_from_reference(reference, authorized).quote == "a"
        extraction.result = {"entities": [{**initial.entities[0].model_dump(), "evidence": {"start": 0, "end": 1, "quote": "x"}}]}
        assert evidence_from_reference(reference, authorized) is None
        extraction.result = initial.model_dump()
        item.title, item.review = "Edited title", "Reviewed"
        item.content += "Outside both cutoffs"
        db.session.commit()
        indexing.reconcile()
        assert {kind: index_record.fingerprint for kind, index_record in indexes.items()} == original
        assert extraction.status == "ready"

        classification = NewsItemAttribute(key="classification", value="general news")
        item.attributes.append(classification)
        db.session.commit()
        assert indexing.submit(extraction.id, result)[1] == 409
        db.session.rollback()
        indexing.reconcile()
        assert extraction.fingerprint != original["extraction"]
        assert embedding.fingerprint == original["embedding"]
        job = indexing.claim(extraction.id)
        assert job["extraction_profile"] == "general"
        cyber_only = CompactExtractionResult.model_validate(
            {
                "entities": [{"id": "a", "name": "a", "type": "ORG"}, {"id": "b", "name": "b", "type": "ORG"}],
                "relations": [{"source_id": "a", "target_id": "b", "type": "ATTACKS", "quote": "a", "assertion": "affirmed"}],
            }
        ).resolve(job["content"])
        assert (
            indexing.submit(extraction.id, IndexSubmission(token=job["token"], fingerprint=job["fingerprint"], extraction=cyber_only))[1]
            == 400
        )
        result = IndexSubmission(token=job["token"], fingerprint=job["fingerprint"], extraction=ExtractionResult())
        assert indexing.submit(extraction.id, result)[1] == 200
        original["extraction"] = extraction.fingerprint
        classification.value = "other"
        db.session.commit()
        indexing.reconcile()
        assert extraction.status == "ready" and extraction.fingerprint == original["extraction"]

        item.content = "a" * 10000 + "changed inside extraction"
        db.session.commit()
        indexing.reconcile()
        assert embedding.fingerprint == original["embedding"]
        assert extraction.fingerprint != original["extraction"]
        assert indexing.submit(extraction.id, result)[1] == 409
        db.session.rollback()
        # Simulate a lost RQ job and an expired durable lease.
        extraction.lease_until = HragIndex.utcnow() - timedelta(seconds=1)
        db.session.commit()
        assert indexing.reconcile()["queued"] >= 1
        fresh = indexing.claim(extraction.id)
        failure = IndexSubmission(token=fresh["token"], fingerprint=fresh["fingerprint"], failed=True)
        assert indexing.submit(extraction.id, failure)[1] == 200
        assert extraction.status == "pending" and extraction.retry_after > HragIndex.utcnow()

        configured_index["llm_endpoints"]["embed"]["api_formats"]["embeddings"]["dimensions"] = 2
        indexing.reconcile()
        generations = list(db.session.scalars(db.select(HragGeneration).where(HragGeneration.pipeline == "embedding")))
        assert len(generations) == 2
        pending = next(g for g in generations if not g.active)
        assert pending.config["dimensions"] == 2
        active_embedding = db.session.get(HragGeneration, embedding.generation_id)
        assert active_embedding.active and active_embedding.config["dimensions"] == 3
        assert indexing.generation_endpoint(active_embedding)["dimensions"] == 3
        pending_index = db.session.scalar(
            db.select(HragIndex).where(HragIndex.generation_id == pending.id, HragIndex.news_item_id == item.id)
        )
        assert indexing.claim(pending_index.id)["dimensions"] == 2
        assert indexing.activate(pending.id)[1] == 409
        db.session.rollback()
        configured_index["llm_endpoints"]["verify"]["api_key"] = "rotated-key"
        configured_index["llm_endpoints"]["verify"]["api_formats"]["systemone"]["model"] = "replacement-verifier"
        configured_index["hrag_extraction_reasoning_effort"] = "none"
        indexing.reconcile()
        extraction_generations = list(db.session.scalars(db.select(HragGeneration).where(HragGeneration.pipeline == "extraction")))
        assert len(extraction_generations) == 2
        original_generation = db.session.get(HragGeneration, extraction.generation_id)
        frozen = indexing.generation_verification_endpoint(original_generation)
        assert frozen["model"] == "verify" and frozen["api_key"] == "rotated-key"
        assert "api_key" not in original_generation.config["verification"]
        replacement = next(g for g in extraction_generations if not g.active)
        assert replacement.config["reasoning_effort"] == "none"
        assert replacement.config["verification"]["model"] == "replacement-verifier"
        configured_index["llm_endpoints"]["verify"]["enabled"] = False
        assert indexing.generation_verification_endpoint(original_generation) is None
        assert indexing.current_configuration("extraction", configured_index) is None
        assert indexing.current_configuration("embedding", configured_index) is not None
        configured_index["hrag_relationship_verification_enabled"] = False
        configured_index["llm_extraction_verification_endpoint"] = ""
        del configured_index["llm_endpoints"]["verify"]
        indexing.reconcile()
        unverified = db.session.scalar(
            db.select(HragGeneration).where(HragGeneration.pipeline == "extraction").order_by(HragGeneration.created.desc())
        )
        assert unverified.id not in {original_generation.id, replacement.id}
        assert unverified.config["verification"] is None and not unverified.active
        assert original_generation.active
        assert indexing.index_status()["configuration_errors"] == []
        unverified_index = db.session.scalar(
            db.select(HragIndex).where(HragIndex.generation_id == unverified.id, HragIndex.news_item_id == item.id)
        )
        job = IndexJob.model_validate(indexing.claim(unverified_index.id))
        assert job.verification_endpoint is None
        assert (
            indexing.submit(
                unverified_index.id, IndexSubmission(token=job.token, fingerprint=job.fingerprint, extraction=ExtractionResult())
            )[1]
            == 200
        )
        configured_index["hrag_relationship_verification_enabled"] = True
        assert indexing.current_configuration("extraction", configured_index) is None
        assert indexing.index_status()["configuration_errors"]
        db.session.delete(item)
        db.session.commit()
        assert not list(db.session.scalars(db.select(HragIndex).where(HragIndex.news_item_id == item.id)))
    finally:
        db.session.delete(story)
        db.session.commit()


def test_runtime_chunk_sizes_build_independent_generations(configured_index, monkeypatch):
    content = "First paragraph. " * 50 + "\n\n" + "Relevant final paragraph. " * 50
    story = create_story(news_items=[build_news_item_payload(content=content)])
    saved = Mock()
    monkeypatch.setattr(indexing, "save_chunks", saved)
    layouts = ((2000, True), (500, True), (3000, True), (500, False))
    counts = []
    original_active = None
    try:
        for size, enabled in layouts:
            configured_index.update(hrag_chunk_size=size, hrag_chunk_overlap=100, hrag_chunking_enabled=enabled)
            indexing.reconcile()
            generation = db.session.scalar(
                db.select(HragGeneration).where(HragGeneration.pipeline == "embedding").order_by(HragGeneration.created.desc())
            )
            if original_active is None:
                original_active = generation.id
            else:
                assert db.session.get(HragGeneration, original_active).active
                assert not generation.active
            index_record = db.session.scalar(
                db.select(HragIndex).where(HragIndex.generation_id == generation.id, HragIndex.news_item_id == story.news_items[0].id)
            )
            job = indexing.claim(index_record.id)
            counts.append(len(job["chunks"]))
            if not enabled:
                assert job["chunks"] == [{"start": 0, "end": len(content)}]
            chunks = [ChunkEmbedding(**span, embedding=[1, 0, 0]) for span in job["chunks"]]
            submission = IndexSubmission(token=job["token"], fingerprint=job["fingerprint"], chunks=chunks)
            invalid = submission.model_copy(deep=True)
            invalid.chunks[0].end -= 1
            assert indexing.submit(index_record.id, invalid)[1] == 400
            db.session.rollback()
            assert indexing.submit(index_record.id, submission)[1] == 200
            assert saved.call_args.args[1] == chunks
            assert indexing.submit(index_record.id, submission)[1] == 200
            reference = EvidenceReference(
                citation="V1", index_id=index_record.id, fingerprint=index_record.fingerprint, chunk_index=len(chunks) - 1
            )
            evidence = evidence_from_reference(reference, {index_record.id: (index_record, generation, story.news_items[0])})
            assert evidence.quote == content[chunks[-1].start : chunks[-1].end]
            assert evidence.chunk_index == len(chunks) - 1
        assert counts[1] > counts[0] > counts[2]
        assert counts[3] == 1
        remaining = list(
            db.session.scalars(db.select(HragIndex).where(HragIndex.generation_id == generation.id, HragIndex.status != "ready"))
        )
        for pending in remaining:
            job = indexing.claim(pending.id)
            if job:
                result = IndexSubmission(
                    token=job["token"],
                    fingerprint=job["fingerprint"],
                    chunks=[ChunkEmbedding(**span, embedding=[1, 0, 0]) for span in job["chunks"]],
                )
                assert indexing.submit(pending.id, result)[1] == 200
        assert indexing.activate(generation.id)[1] == 200
        assert not db.session.get(HragGeneration, original_active).active
        assert db.session.get(HragGeneration, generation.id).active
    finally:
        db.session.delete(story)
        db.session.commit()


def test_backfill_drains_dispatch_batches_and_continues_scans(configured_index, monkeypatch):
    from core.managers.queue_manager import queue_manager

    story = create_story(news_items=[build_news_item_payload(content=f"Index item {number}.") for number in range(51)])
    item_ids = [item.id for item in story.news_items]
    try:
        indexing.reconcile()
        generations = list(db.session.scalars(db.select(HragGeneration)))
        for generation in generations:
            records = list(db.session.scalars(db.select(HragIndex).where(HragIndex.generation_id == generation.id)))
            assert sum(record.status == "queued" for record in records) == 50
            assert sum(record.status == "pending" for record in records) > 0
            assert sum(record.news_item_id in item_ids for record in records) == 51
            for _ in records:
                record = next(record for record in records if record.status == "queued")
                job = indexing.claim(record.id)
                if job is None:
                    assert record.status == "ready"
                    continue
                submission = IndexSubmission(token=job["token"], fingerprint=job["fingerprint"])
                if generation.pipeline == "extraction":
                    submission.extraction = ExtractionResult()
                else:
                    submission.chunks = [ChunkEmbedding(**span, embedding=[1, 0, 0]) for span in job["chunks"]]
                assert indexing.submit(record.id, submission)[1] == 200
            assert all(record.status == "ready" for record in records)
        generation = next(generation for generation in generations if generation.pipeline == "embedding")
        assert indexing.reprocess(generation.id)[1] == 200
        assert queue_manager.enqueue_task.call_args.kwargs["generation_id"] == generation.id
        monkeypatch.setattr(indexing, "SCAN_BATCH_SIZE", 25)
        for _ in range(2):
            indexing.reconcile(generation.id)
            assert generation.cursor and not generation.scanned
            assert queue_manager.enqueue_task.call_args.kwargs["generation_id"] == generation.id
        indexing.reconcile(generation.id)
        assert generation.cursor == "" and generation.scanned
        assert len(list(db.session.scalars(db.select(HragGeneration)))) == 2
    finally:
        db.session.delete(story)
        db.session.commit()
