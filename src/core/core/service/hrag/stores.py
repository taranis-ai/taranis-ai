"""Database-specific HRAG operations. All retrieval receives authorized keys."""

import json
from contextlib import contextmanager
from typing import LiteralString

from models.hrag import ChunkEmbedding, ExtractionResult, GraphPlan, entity_identity
from neo4j import GraphDatabase, Query
from sqlalchemy import String, bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY

from core.config import Config
from core.managers.db_manager import db


def initialize_vectors(engine):
    if not Config.HRAG_ENABLED:
        return
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.execute(
            text("""CREATE TABLE IF NOT EXISTS hrag_chunk_vector (
            work_id varchar(36) NOT NULL REFERENCES hrag_work(id) ON DELETE CASCADE,
            chunk_index integer NOT NULL,
            start_offset integer NOT NULL,
            end_offset integer NOT NULL,
            embedding vector NOT NULL,
            PRIMARY KEY (work_id, chunk_index)
        )""")
        )


def save_chunks(work_id: str, chunks: list[ChunkEmbedding]):
    if db.engine.dialect.name != "postgresql":
        return
    db.session.execute(text("DELETE FROM hrag_chunk_vector WHERE work_id = :id"), {"id": work_id})
    if chunks:
        db.session.execute(
            text("""INSERT INTO hrag_chunk_vector (work_id, chunk_index, start_offset, end_offset, embedding)
            VALUES (:id, :index, :start, :end, CAST(:vector AS vector))"""),
            [
                {"id": work_id, "index": index, "start": chunk.start, "end": chunk.end, "vector": json.dumps(chunk.embedding)}
                for index, chunk in enumerate(chunks)
            ],
        )


def search_chunk_vectors(vector: list[float], allowed_ids: list[str], limit: int, per_item: int) -> list[tuple[str, int]]:
    if not allowed_ids:
        return []
    query = text("""WITH ranked AS (
        SELECT work_id, chunk_index, embedding <=> CAST(:vector AS vector) AS distance,
        row_number() OVER (PARTITION BY work_id ORDER BY embedding <=> CAST(:vector AS vector), chunk_index) AS item_rank
        FROM hrag_chunk_vector WHERE work_id = ANY(:ids)
    ) SELECT work_id, chunk_index FROM ranked WHERE item_rank <= :per_item
    ORDER BY distance, work_id, chunk_index LIMIT :limit""").bindparams(bindparam("ids", type_=ARRAY(String())))
    return [
        (row[0], row[1])
        for row in db.session.execute(query, {"ids": allowed_ids, "vector": json.dumps(vector), "limit": limit, "per_item": per_item})
    ]


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
