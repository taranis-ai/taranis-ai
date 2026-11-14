"""Database-specific HRAG operations. All retrieval receives authorized keys."""

import json
from contextlib import contextmanager
from typing import LiteralString

from models.hrag import ExtractionResult, GraphPlan, entity_identity
from neo4j import GraphDatabase, Query
from sqlalchemy import String, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY

from core.config import Config
from core.managers.db_manager import db


def initialize_vectors(engine):
    if not Config.HRAG_ENABLED:
        return
    if engine.dialect.name != "postgresql":
        return  # Unit fixtures use SQLite; production retrieval requires PostgreSQL.
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.execute(
            text("""CREATE TABLE IF NOT EXISTS hrag_vector (
            work_id varchar(36) PRIMARY KEY REFERENCES hrag_work(id) ON DELETE CASCADE,
            embedding vector NOT NULL
        )""")
        )


def save_vector(work_id: str, vector: list[float]):
    if db.engine.dialect.name != "postgresql":
        return
    db.session.execute(
        text("""INSERT INTO hrag_vector (work_id, embedding) VALUES (:id, CAST(:vector AS vector))
        ON CONFLICT (work_id) DO UPDATE SET embedding = excluded.embedding"""),
        {"id": work_id, "vector": json.dumps(vector)},
    )


def vector_search(vector: list[float], allowed_ids: list[str], limit: int) -> list[str]:
    if not allowed_ids:
        return []
    # Exact search over the authorized generation avoids ANN post-filter underfill.
    statement = text("""SELECT work_id FROM hrag_vector WHERE work_id = ANY(:ids)
        ORDER BY embedding <=> CAST(:vector AS vector), work_id LIMIT :limit""").bindparams(bindparam("ids", type_=ARRAY(String())))
    return list(db.session.scalars(statement, {"ids": allowed_ids, "vector": json.dumps(vector), "limit": limit}))


@contextmanager
def graph_driver():
    with GraphDatabase.driver(
        Config.HRAG_NEO4J_URI,
        auth=(Config.HRAG_NEO4J_USER, Config.HRAG_NEO4J_PASSWORD),
        connection_timeout=5,
        connection_acquisition_timeout=10,
        max_transaction_retry_time=0,
    ) as driver:
        yield driver


def project_graph(work_id: str, fingerprint: str, news_item_id: str, generation: str, result: ExtractionResult):
    key = f"{work_id}:{fingerprint}"
    entities = {entity.id: entity for entity in result.entities}
    identities = {eid: entity_identity(entity, news_item_id, generation + fingerprint) for eid, entity in entities.items()}
    mentions = [{"id": identities[e.id], "name": e.name.casefold(), "type": e.type} for e in result.entities]
    relations = [
        {
            "source": identities[r.source_id],
            "target": identities[r.target_id],
            "type": r.type,
            "assertion": r.assertion,
            "index": index,
            "date": r.date,
        }
        for index, r in enumerate(result.relations)
    ]
    with graph_driver() as driver, driver.session(database=Config.HRAG_NEO4J_DATABASE) as session:
        session.run("CREATE CONSTRAINT hrag_entity_id IF NOT EXISTS FOR (n:HEntity) REQUIRE n.id IS UNIQUE").consume()
        session.run("CREATE CONSTRAINT hrag_document_key IF NOT EXISTS FOR (n:HDocument) REQUIRE n.key IS UNIQUE").consume()

        def write(tx):
            # Lock this projection before replacing assertions; duplicate callbacks serialize.
            tx.run("MERGE (d:HDocument {key: $key}) SET d.work_id = $id, d.lock = true", key=key, id=work_id).consume()
            tx.run("MATCH ()-[r:H_ASSERTION {key: $key}]->() DELETE r", key=key).consume()
            tx.run("MATCH (d:HDocument {key: $key})-[r:H_MENTIONS]->() DELETE r", key=key).consume()
            tx.run(
                """MERGE (d:HDocument {key: $key}) SET d.work_id = $id
                WITH d UNWIND $mentions AS mention
                MERGE (n:HEntity {id: mention.id}) SET n.name = mention.name, n.entity_type = mention.type
                MERGE (d)-[:H_MENTIONS]->(n)""",
                key=key,
                id=work_id,
                mentions=mentions,
            ).consume()
            tx.run(
                """UNWIND $relations AS relation
                MATCH (s:HEntity {id: relation.source}), (t:HEntity {id: relation.target})
                CREATE (s)-[r:H_ASSERTION]->(t)
                SET r.key = $key, r.work_id = $id, r.kind = relation.type,
                    r.assertion = relation.assertion, r.idx = relation.index, r.date = relation.date""",
                key=key,
                id=work_id,
                relations=relations,
            ).consume()

        session.execute_write(write)


def compile_graph(plan: GraphPlan) -> LiteralString:
    """Select a fixed query; every plan value is a bound parameter."""
    if plan.hops == 0:
        return """MATCH (d:HDocument)-[:H_MENTIONS]->(n:HEntity)
            WHERE d.key IN $allowed
              AND (size($names) = 0 OR any(name IN $names WHERE n.name CONTAINS name))
              AND (size($types) = 0 OR n.entity_type IN $types)
            RETURN DISTINCT [{key: d.key, work_id: d.work_id, idx: null}] AS evidence
            ORDER BY evidence[0].key LIMIT $limit"""
    return """MATCH p=(n:HEntity)-[:H_ASSERTION*1..3]-(m:HEntity)
        WHERE length(p) <= $hops AND all(r IN relationships(p) WHERE r.key IN $allowed
            AND (size($relations) = 0 OR r.kind IN $relations)
            AND (length(p) = 1 OR (r.assertion = 'affirmed' AND r.kind <> 'ALIAS_OF')))
          AND (size($names) = 0 OR any(name IN $names WHERE n.name CONTAINS name))
          AND (size($types) = 0 OR n.entity_type IN $types)
        RETURN DISTINCT [r IN relationships(p) | {key: r.key, work_id: r.work_id, idx: r.idx}] AS evidence
        ORDER BY size(evidence), evidence[0].key LIMIT $limit"""


def graph_search(plan: GraphPlan, allowed_keys: list[str], limit: int, timeout: float = 30) -> list[list[dict]]:
    if not allowed_keys:
        return []
    with graph_driver() as driver, driver.session(database=Config.HRAG_NEO4J_DATABASE) as session:
        result = session.run(
            Query(compile_graph(plan), timeout=timeout),
            allowed=allowed_keys,
            hops=plan.hops,
            names=plan.names,
            types=plan.entity_types,
            relations=plan.relationships,
            limit=limit,
        )
        return [record["evidence"] for record in result]


def prune_graph(valid_keys: list[str]):
    with graph_driver() as driver, driver.session(database=Config.HRAG_NEO4J_DATABASE) as session:
        session.run("MATCH ()-[r:H_ASSERTION]->() WHERE NOT r.key IN $keys DELETE r", keys=valid_keys).consume()
        session.run("MATCH (d:HDocument) WHERE NOT d.key IN $keys DETACH DELETE d", keys=valid_keys).consume()
        session.run("MATCH (n:HEntity) WHERE NOT (n)--() DELETE n").consume()


def graph_document_keys() -> set[str]:
    with graph_driver() as driver, driver.session(database=Config.HRAG_NEO4J_DATABASE) as session:
        return {row["key"] for row in session.run(Query("MATCH (d:HDocument) RETURN d.key AS key", timeout=30))}
