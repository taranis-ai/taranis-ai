"""Opt-in real-store check; database names/credentials must refer to disposable services."""

import os
import uuid

import pytest
from flask import Flask
from models.hrag import ExtractionResult, GraphPlan
from sqlalchemy import text

from core.config import Config
from core.managers.db_manager import db
from core.service.hrag import stores


@pytest.fixture
def hrag_stores(monkeypatch):
    uri = os.environ.get("HRAG_TEST_POSTGRES_URI")
    bolt = os.environ.get("HRAG_TEST_NEO4J_URI")
    if not uri or not bolt:
        pytest.skip("Set HRAG_TEST_POSTGRES_URI and HRAG_TEST_NEO4J_URI for disposable database checks")
    monkeypatch.setattr(Config, "HRAG_ENABLED", True)
    monkeypatch.setattr(Config, "HRAG_NEO4J_URI", bolt)
    monkeypatch.setattr(Config, "HRAG_NEO4J_PASSWORD", os.environ["HRAG_TEST_NEO4J_PASSWORD"])
    app = Flask("hrag-store-check")
    schema = "hrag_test_" + uuid.uuid4().hex
    app.config.update(SQLALCHEMY_DATABASE_URI=uri, SQLALCHEMY_ENGINE_OPTIONS={"connect_args": {"options": f"-csearch_path={schema},public"}})
    db.init_app(app)
    with app.app_context():
        with db.engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            conn.execute(text("CREATE TABLE hrag_work (id varchar(36) PRIMARY KEY)"))
        stores.initialize_vectors(db.engine)
        yield schema
        db.session.remove()
        with db.engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        with stores.graph_driver() as driver:
            driver.execute_query("MATCH (d:HDocument) WHERE d.work_id STARTS WITH $prefix DETACH DELETE d", prefix=schema)
            driver.execute_query("MATCH ()-[r:H_ASSERTION]->() WHERE r.work_id STARTS WITH $prefix DELETE r", prefix=schema)
            driver.execute_query("MATCH (n:HEntity) WHERE NOT (n)--() DELETE n")
        db.engine.dispose()


def test_authorized_paths_vector_ranking_projection_retry_and_deletion(hrag_stores):
    prefix = hrag_stores
    ids = [str(uuid.uuid4()) for _ in range(3)]
    for work_id, vector in zip(ids, ([1, 0, 0], [0.9, 0.1, 0], [0, 1, 0]), strict=True):
        db.session.execute(text("INSERT INTO hrag_work (id) VALUES (:id)"), {"id": work_id})
        stores.save_vector(work_id, vector)
    db.session.commit()
    assert stores.vector_search([1, 0, 0], ids[1:], 1) == [ids[1]]  # Hidden nearest neighbor cannot consume the limit.
    stores.save_vector(ids[1], [0, 0, 1])
    db.session.commit()
    db.session.execute(text("DELETE FROM hrag_work WHERE id = :id"), {"id": ids[1]})
    db.session.commit()
    assert stores.vector_search([1, 0, 0], ids[1:], 3) == [ids[2]]

    keys = []
    for index, (actor, assertion) in enumerate((("Alpha", "affirmed"), ("Beta", "affirmed"), ("Gamma", "negated"))):
        content = f"{actor} exploits CVE-2026-9999." if assertion == "affirmed" else f"{actor} does not exploit CVE-2026-9999."
        cve_start = content.index("CVE")
        result = ExtractionResult.model_validate(
            {
                "entities": [
                    {"id": "a", "type": "GROUP", "name": actor, "evidence": {"start": 0, "end": len(actor), "quote": actor}},
                    {
                        "id": "v",
                        "type": "VULNERABILITY",
                        "name": "CVE-2026-9999",
                        "evidence": {"start": cve_start, "end": cve_start + 13, "quote": "CVE-2026-9999"},
                    },
                ],
                "relations": [
                    {
                        "type": "EXPLOITS",
                        "source_id": "a",
                        "target_id": "v",
                        "assertion": assertion,
                        "evidence": {"start": 0, "end": len(content), "quote": content},
                    }
                ],
            }
        ).validate_content(content)
        work_id = f"{prefix}-{index}"
        stores.project_graph(work_id, "current", str(index), prefix, result)
        stores.project_graph(work_id, "current", str(index), prefix, result)  # Idempotent replay.
        keys.append(f"{work_id}:current")
    plan = GraphPlan(names=["Alpha"], hops=3)
    full = stores.graph_search(plan, keys, 50)
    assert any(len(path) == 2 for path in full)
    assert not any(row["key"] == keys[2] for path in full for row in path)
    filtered = stores.graph_search(plan, [keys[0]], 50)
    assert len(filtered) == 1 and len(filtered[0]) == 1
    assert stores.graph_search(GraphPlan(names=["'; MATCH (n) DETACH DELETE n //"]), keys, 50) == []
    assert stores.graph_search(plan, [], 50) == []
    # A stale callback creates its own fingerprint projection and cannot replace current evidence.
    stores.project_graph(f"{prefix}-0", "old", "0", prefix, result)
    assert stores.graph_search(plan, [keys[0]], 50) == filtered
