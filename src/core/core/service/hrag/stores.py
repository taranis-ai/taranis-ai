"""Database-specific HRAG operations. All retrieval receives authorized keys."""

import json
from contextlib import contextmanager
from typing import LiteralString

from models.hrag import RELATION_ENDPOINTS, ChunkEmbedding, ExtractionResult, GraphPlan, entity_identity
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
            text("""CREATE TABLE IF NOT EXISTS news_item_chunk_embedding (
            index_id varchar(36) NOT NULL REFERENCES hrag_index(id) ON DELETE CASCADE,
            chunk_index integer NOT NULL,
            start_offset integer NOT NULL,
            end_offset integer NOT NULL,
            embedding vector NOT NULL,
            PRIMARY KEY (index_id, chunk_index)
        )""")
        )


def save_chunks(index_id: str, chunks: list[ChunkEmbedding]):
    if db.engine.dialect.name != "postgresql":
        return
    db.session.execute(text("DELETE FROM news_item_chunk_embedding WHERE index_id = :id"), {"id": index_id})
    if chunks:
        db.session.execute(
            text("""INSERT INTO news_item_chunk_embedding (index_id, chunk_index, start_offset, end_offset, embedding)
            VALUES (:id, :index, :start, :end, CAST(:vector AS vector))"""),
            [
                {"id": index_id, "index": index, "start": chunk.start, "end": chunk.end, "vector": json.dumps(chunk.embedding)}
                for index, chunk in enumerate(chunks)
            ],
        )


def search_chunk_vectors(vector: list[float], allowed_ids: list[str], limit: int, per_item: int) -> list[tuple[str, int]]:
    if not allowed_ids:
        return []
    query = text("""WITH ranked AS (
        SELECT index_id, chunk_index, embedding <=> CAST(:vector AS vector) AS distance,
        row_number() OVER (PARTITION BY index_id ORDER BY embedding <=> CAST(:vector AS vector), chunk_index) AS item_rank
        FROM news_item_chunk_embedding WHERE index_id = ANY(:ids)
    ) SELECT index_id, chunk_index FROM ranked WHERE item_rank <= :per_item
    ORDER BY distance, index_id, chunk_index LIMIT :limit""").bindparams(bindparam("ids", type_=ARRAY(String())))
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


def project_graph(index_id: str, fingerprint: str, news_item_id: str, generation: str, result: ExtractionResult):
    key = f"{index_id}:{fingerprint}"
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
        session.run("CREATE CONSTRAINT hrag_entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE").consume()
        session.run("CREATE CONSTRAINT hrag_document_key IF NOT EXISTS FOR (n:Document) REQUIRE n.key IS UNIQUE").consume()

        def write(tx):
            # Lock this projection before replacing assertions; duplicate callbacks serialize.
            tx.run("MERGE (d:Document {key: $key}) SET d.index_id = $id, d.lock = true", key=key, id=index_id).consume()
            tx.run(
                "MATCH (:Entity)-[r:$any($relations) {key: $key}]->(:Entity) DELETE r",
                key=key,
                relations=list(RELATION_ENDPOINTS),
            ).consume()
            tx.run("MATCH (d:Document {key: $key})-[r:MENTIONS]->() DELETE r", key=key).consume()
            tx.run(
                """MERGE (d:Document {key: $key}) SET d.index_id = $id
                WITH d UNWIND $mentions AS mention
                MERGE (n:Entity {id: mention.id}) SET n.name = mention.name, n.entity_type = mention.type
                MERGE (d)-[:MENTIONS]->(n)""",
                key=key,
                id=index_id,
                mentions=mentions,
            ).consume()
            tx.run(
                """UNWIND $relations AS relation
                MATCH (s:Entity {id: relation.source}), (t:Entity {id: relation.target})
                CREATE (s)-[r:$(relation.type)]->(t)
                SET r.key = $key, r.index_id = $id,
                    r.assertion = relation.assertion, r.idx = relation.index, r.date = relation.date""",
                key=key,
                id=index_id,
                relations=relations,
            ).consume()

        session.execute_write(write)


def compile_graph(plan: GraphPlan) -> LiteralString:
    """Select a fixed query; every plan value is a bound parameter."""
    if plan.hops == 0:
        return """MATCH (d:Document)-[:MENTIONS]->(n:Entity)
            WHERE d.key IN $allowed
              AND (size($names) = 0 OR any(name IN $names WHERE n.name CONTAINS name))
              AND (size($types) = 0 OR n.entity_type IN $types)
            RETURN DISTINCT [{key: d.key, index_id: d.index_id, idx: null}] AS evidence
            ORDER BY evidence[0].key LIMIT $limit"""
    return """MATCH p=(n:Entity)-[*1..3]-(m:Entity)
        WHERE length(p) <= $hops AND all(r IN relationships(p) WHERE r.key IN $allowed
            AND type(r) IN $relations
            AND (length(p) = 1 OR (r.assertion = 'affirmed' AND type(r) <> 'ALIAS_OF')))
          AND (size($names) = 0 OR any(name IN $names WHERE n.name CONTAINS name))
          AND (size($types) = 0 OR n.entity_type IN $types)
        RETURN DISTINCT [r IN relationships(p) | {key: r.key, index_id: r.index_id, idx: r.idx}] AS evidence
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
            relations=plan.relationships or list(RELATION_ENDPOINTS),
            limit=limit,
        )
        return [record["evidence"] for record in result]


def prune_graph(valid_keys: list[str]):
    with graph_driver() as driver, driver.session(database=Config.HRAG_NEO4J_DATABASE) as session:
        session.run(
            "MATCH (:Entity)-[r:$any($relations)]->(:Entity) WHERE NOT r.key IN $keys DELETE r",
            keys=valid_keys,
            relations=list(RELATION_ENDPOINTS),
        ).consume()
        session.run("MATCH (d:Document) WHERE NOT d.key IN $keys DETACH DELETE d", keys=valid_keys).consume()
        session.run("MATCH (n:Entity) WHERE NOT (n)--() DELETE n").consume()


def graph_document_keys() -> set[str]:
    with graph_driver() as driver, driver.session(database=Config.HRAG_NEO4J_DATABASE) as session:
        return {row["key"] for row in session.run(Query("MATCH (d:Document) RETURN d.key AS key", timeout=30))}
