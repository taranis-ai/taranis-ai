from datetime import timedelta
from unittest.mock import Mock

import pytest
from models.hrag import ExtractionResult, IndexSubmission

from core.config import Config
from core.managers.db_manager import db
from core.model.hrag import HragGeneration, HragWork
from core.model.settings import Settings
from core.service.hrag import indexing
from tests.application.support.builders import build_news_item_payload, create_story


@pytest.fixture
def configured_index(db_persistent_session, monkeypatch):
    monkeypatch.setattr(Config, "HRAG_ENABLED", True)
    monkeypatch.setattr(Config, "HRAG_EMBEDDING_DIMENSIONS", 3)
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
                    "api_formats": {"embeddings": {"model": "embed"}},
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
        }
    )
    monkeypatch.setattr(Settings, "get_settings", classmethod(lambda cls: settings))
    monkeypatch.setattr("core.managers.queue_manager.queue_manager.enqueue_task", Mock(return_value=True))
    monkeypatch.setattr(indexing, "prune_graph", Mock())
    monkeypatch.setattr(indexing, "project_graph", Mock())
    monkeypatch.setattr(indexing, "graph_document_keys", lambda: {w.graph_key for w in db.session.scalars(db.select(HragWork))})
    yield settings
    db.session.rollback()
    db.session.execute(db.delete(HragGeneration))
    db.session.commit()


def test_durable_index_lifecycle_cutoffs_retries_and_generations(configured_index):
    story = create_story(news_items=[build_news_item_payload(content="a" * 4000 + "b" * 16000)])
    item = story.news_items[0]
    try:
        indexing.reconcile()
        from core.managers.queue_manager import queue_manager

        assert {call.args[0] for call in queue_manager.enqueue_task.call_args_list} == {"embeddings", "hrag"}
        works = {
            db.session.get(HragGeneration, w.generation_id).pipeline: w
            for w in db.session.scalars(db.select(HragWork).where(HragWork.news_item_id == item.id))
        }
        extraction, embedding = works["extraction"], works["embedding"]
        assert db.session.get(HragGeneration, extraction.generation_id).config["schema"] == "v3"
        assert db.session.get(HragGeneration, embedding.generation_id).config["schema"] == "v1"
        original = {kind: work.fingerprint for kind, work in works.items()}
        job = indexing.claim(extraction.id)
        assert job and indexing.claim(extraction.id) is None
        assert job["reasoning_effort"] == "none"
        assert job["verification_endpoint"]["model"] == "verify"
        result = IndexSubmission(token=job["token"], fingerprint=job["fingerprint"], extraction=ExtractionResult())
        assert indexing.submit(extraction.id, result)[1] == 200
        assert indexing.submit(extraction.id, result)[1] == 200
        item.title, item.review = "Edited title", "Reviewed"
        item.content += "Outside both cutoffs"
        db.session.commit()
        indexing.reconcile()
        assert {kind: work.fingerprint for kind, work in works.items()} == original
        assert extraction.status == "ready"

        item.content = "a" * 4000 + "changed inside extraction"
        db.session.commit()
        indexing.reconcile()
        assert embedding.fingerprint == original["embedding"]
        assert extraction.fingerprint != original["extraction"]
        assert indexing.submit(extraction.id, result)[1] == 409
        db.session.rollback()
        # Simulate a lost RQ job and an expired durable lease.
        extraction.lease_until = HragWork.utcnow() - timedelta(seconds=1)
        db.session.commit()
        assert indexing.reconcile()["queued"] >= 1
        fresh = indexing.claim(extraction.id)
        failure = IndexSubmission(token=fresh["token"], fingerprint=fresh["fingerprint"], failed=True)
        assert indexing.submit(extraction.id, failure)[1] == 200
        assert extraction.status == "pending" and extraction.retry_after > HragWork.utcnow()

        configured_index["llm_endpoints"]["embed"]["api_formats"]["embeddings"]["model"] = "replacement"
        indexing.reconcile()
        generations = list(db.session.scalars(db.select(HragGeneration).where(HragGeneration.pipeline == "embedding")))
        assert len(generations) == 2
        pending = next(g for g in generations if not g.active)
        assert indexing.activate(pending.id)[1] == 409
        db.session.rollback()
        configured_index["llm_endpoints"]["verify"]["api_key"] = "rotated-key"
        configured_index["llm_endpoints"]["verify"]["api_formats"]["systemone"]["model"] = "replacement-verifier"
        configured_index["hrag_extraction_reasoning_effort"] = "low"
        indexing.reconcile()
        extraction_generations = list(db.session.scalars(db.select(HragGeneration).where(HragGeneration.pipeline == "extraction")))
        assert len(extraction_generations) == 2
        original_generation = db.session.get(HragGeneration, extraction.generation_id)
        frozen = indexing.generation_verification_endpoint(original_generation)
        assert frozen["model"] == "verify" and frozen["api_key"] == "rotated-key"
        assert "api_key" not in original_generation.config["verification"]
        replacement = next(g for g in extraction_generations if not g.active)
        assert replacement.config["reasoning_effort"] == "low"
        assert replacement.config["verification"]["model"] == "replacement-verifier"
        configured_index["llm_endpoints"]["verify"]["enabled"] = False
        assert indexing.generation_verification_endpoint(original_generation) is None
        assert indexing.current_configuration("extraction", configured_index) is None
        assert indexing.current_configuration("embedding", configured_index) is not None
        db.session.delete(item)
        db.session.commit()
        assert not list(db.session.scalars(db.select(HragWork).where(HragWork.news_item_id == item.id)))
    finally:
        db.session.delete(story)
        db.session.commit()
