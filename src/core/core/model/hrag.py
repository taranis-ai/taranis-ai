import json
import re
from typing import Any

from models.hrag import DEFAULT_HRAG_SCHEMA, HragSchema
from sqlalchemy import UniqueConstraint, text
from sqlalchemy.orm import Mapped, aliased, relationship
from sqlalchemy.types import TypeDecorator, UserDefinedType

from core.log import logger
from core.managers.db_manager import db
from core.model.base_model import UUID_STR_LENGTH, BaseModel


class Vector(TypeDecorator):
    impl = db.Text
    cache_ok = True

    def process_bind_param(self, value: list[float] | None, dialect) -> str | None:
        if value is None:
            return None
        return "[" + ",".join(str(float(item)) for item in value) + "]"

    def process_result_value(self, value: str | list[float] | None, dialect) -> list[float] | None:
        if value is None:
            return None
        if isinstance(value, list):
            return [float(item) for item in value]
        return [float(item) for item in json.loads(value)]

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PostgresVector())
        return dialect.type_descriptor(db.Text())


class _PostgresVector(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kwargs) -> str:
        return "vector"


class HragSchemaConfig(BaseModel):
    __tablename__ = "hrag_schema"
    __table_args__ = (UniqueConstraint("version", name="uq_hrag_schema_version"),)

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    version: Mapped[str] = db.Column(db.String(128), nullable=False)
    definition: Mapped[dict[str, Any]] = db.Column(db.JSON, nullable=False)
    active: Mapped[bool] = db.Column(db.Boolean, nullable=False, default=False, index=True)

    @classmethod
    def get_active_schema(cls) -> HragSchema:
        active = cls.get_first(db.select(cls).where(cls.active.is_(True)).order_by(db.desc(cls.version)))
        if active is None:
            active = cls.from_dict({"version": DEFAULT_HRAG_SCHEMA.version, "definition": DEFAULT_HRAG_SCHEMA.model_dump(), "active": True})
            db.session.add(active)
            db.session.commit()
        return HragSchema.model_validate(active.definition)


class HragEmbedding(BaseModel):
    __tablename__ = "hrag_embedding"
    __table_args__ = (UniqueConstraint("news_item_id", "schema_version", name="uq_hrag_embedding_item_schema"),)

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    news_item_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("news_item.id", ondelete="CASCADE"), nullable=False, index=True
    )
    schema_version: Mapped[str] = db.Column(db.String(128), nullable=False, index=True)
    content_hash: Mapped[str] = db.Column(db.String(64), nullable=False)
    embedding: Mapped[list[float]] = db.Column(Vector(), nullable=False)


class HragEntity(BaseModel):
    __tablename__ = "hrag_entity"
    __table_args__ = (UniqueConstraint("schema_version", "entity_type", "normalized_name", name="uq_hrag_entity_identity"),)

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    schema_version: Mapped[str] = db.Column(db.String(128), nullable=False, index=True)
    entity_type: Mapped[str] = db.Column(db.String(128), nullable=False, index=True)
    name: Mapped[str] = db.Column(db.String(2048), nullable=False)
    normalized_name: Mapped[str] = db.Column(db.String(2048), nullable=False)


class HragRelation(BaseModel):
    __tablename__ = "hrag_relation"
    __table_args__ = (UniqueConstraint("schema_version", "subject_id", "predicate", "object_id", name="uq_hrag_relation_identity"),)

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    schema_version: Mapped[str] = db.Column(db.String(128), nullable=False, index=True)
    subject_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("hrag_entity.id"), nullable=False)
    predicate: Mapped[str] = db.Column(db.String(128), nullable=False, index=True)
    object_id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), db.ForeignKey("hrag_entity.id"), nullable=False)
    subject: Mapped[HragEntity] = relationship("HragEntity", foreign_keys=[subject_id])
    object: Mapped[HragEntity] = relationship("HragEntity", foreign_keys=[object_id])


class HragRelationEvidence(BaseModel):
    __tablename__ = "hrag_relation_evidence"
    __table_args__ = (UniqueConstraint("relation_id", "news_item_id", name="uq_hrag_relation_evidence"),)

    id: Mapped[str] = db.Column(db.String(UUID_STR_LENGTH), primary_key=True, default=BaseModel.uuid7_str)
    relation_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("hrag_relation.id", ondelete="CASCADE"), nullable=False, index=True
    )
    news_item_id: Mapped[str] = db.Column(
        db.String(UUID_STR_LENGTH), db.ForeignKey("news_item.id", ondelete="CASCADE"), nullable=False, index=True
    )
    confidence: Mapped[float] = db.Column(db.Float, nullable=False)


class HragIndex:
    @staticmethod
    def upsert(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
        news_item_id = str(payload.get("news_item_id") or "")
        embedding = payload.get("embedding")
        content_hash = str(payload.get("content_hash") or "")
        if not news_item_id or not isinstance(embedding, list) or not embedding or not content_hash:
            return {"error": "news_item_id, content_hash, and embedding are required"}, 400

        schema = HragSchemaConfig.get_active_schema()
        schema_version = schema.version
        item = HragEmbedding.get_first(
            db.select(HragEmbedding).where(HragEmbedding.news_item_id == news_item_id, HragEmbedding.schema_version == schema_version)
        )
        if item is None:
            item = HragEmbedding.from_dict(
                {
                    "news_item_id": news_item_id,
                    "schema_version": schema_version,
                    "content_hash": content_hash,
                    "embedding": embedding,
                }
            )
            db.session.add(item)
        else:
            item.content_hash = content_hash
            item.embedding = embedding

        entity_ids: dict[str, str] = {}
        valid_types = {entity.name for entity in schema.entity_types}
        entities = payload.get("entities") or []
        if not isinstance(entities, list):
            return {"error": "entities must be a list"}, 400
        for entity in entities:
            if not isinstance(entity, dict):
                return {"error": "entities must contain objects"}, 400
            local_id = str(entity.get("id") or "")
            entity_type = str(entity.get("type") or "")
            name = str(entity.get("name") or "").strip()
            if not local_id or not name or entity_type not in valid_types:
                return {"error": "invalid extracted entity"}, 400
            normalized_name = name.casefold()
            stored = HragEntity.get_first(
                db.select(HragEntity).where(
                    HragEntity.schema_version == schema_version,
                    HragEntity.entity_type == entity_type,
                    HragEntity.normalized_name == normalized_name,
                )
            )
            if stored is None:
                stored = HragEntity.from_dict(
                    {
                        "schema_version": schema_version,
                        "entity_type": entity_type,
                        "name": name,
                        "normalized_name": normalized_name,
                    }
                )
                db.session.add(stored)
                db.session.flush()
            entity_ids[local_id] = stored.id

        allowed_relations = {relation.name: relation for relation in schema.relation_types}
        relations = payload.get("relations") or []
        if not isinstance(relations, list):
            return {"error": "relations must be a list"}, 400
        relation_count = 0
        for relation in relations:
            if not isinstance(relation, dict):
                return {"error": "relations must contain objects"}, 400
            predicate = str(relation.get("type") or "")
            source_id = entity_ids.get(str(relation.get("source_id") or ""))
            target_id = entity_ids.get(str(relation.get("target_id") or ""))
            definition = allowed_relations.get(predicate)
            if not source_id or not target_id or definition is None:
                return {"error": "invalid extracted relation"}, 400
            source = HragEntity.get(source_id)
            target = HragEntity.get(target_id)
            if (
                source is None
                or target is None
                or source.entity_type not in definition.source_types
                or target.entity_type not in definition.target_types
            ):
                return {"error": "relation endpoint types violate schema"}, 400
            stored_relation = HragRelation.get_first(
                db.select(HragRelation).where(
                    HragRelation.schema_version == schema_version,
                    HragRelation.subject_id == source_id,
                    HragRelation.predicate == predicate,
                    HragRelation.object_id == target_id,
                )
            )
            if stored_relation is None:
                stored_relation = HragRelation.from_dict(
                    {
                        "schema_version": schema_version,
                        "subject_id": source_id,
                        "predicate": predicate,
                        "object_id": target_id,
                    }
                )
                db.session.add(stored_relation)
                db.session.flush()
            evidence = HragRelationEvidence.get_first(
                db.select(HragRelationEvidence).where(
                    HragRelationEvidence.relation_id == stored_relation.id,
                    HragRelationEvidence.news_item_id == news_item_id,
                )
            )
            confidence = float(relation.get("confidence") or 0)
            if evidence is None:
                db.session.add(
                    HragRelationEvidence.from_dict(
                        {"relation_id": stored_relation.id, "news_item_id": news_item_id, "confidence": confidence}
                    )
                )
            else:
                evidence.confidence = confidence
            relation_count += 1

        db.session.commit()
        HragAge.sync()
        return {"message": "HRAG document indexed", "schema_version": schema_version, "relations": relation_count}, 200

    @staticmethod
    def retrieve(embedding: list[float], user_id: str, limit: int = 20) -> dict[str, Any]:
        from core.model.user import User

        user = User.get(user_id)
        if user is None:
            raise ValueError("HRAG retrieval user was not found")
        rows = db.session.execute(db.select(HragEmbedding)).scalars().all()
        scored = sorted(((HragIndex._cosine_distance(embedding, row.embedding), row) for row in rows), key=lambda value: value[0])[:limit]
        news_item_ids = [row.news_item_id for _, row in scored]
        from core.model.news_item import NewsItem

        news_items = {item.id: item for item in NewsItem.get_bulk(news_item_ids) if item.allowed_with_acl(user, require_write_access=False)}
        passages = [
            {
                "id": f"news-item:{row.news_item_id}",
                "source": news_items[row.news_item_id].link or row.news_item_id,
                "text": "\n\n".join(value for value in (news_items[row.news_item_id].title, news_items[row.news_item_id].content) if value),
                "score": 1 - distance,
            }
            for distance, row in scored
            if row.news_item_id in news_items
        ]
        subject_entity = aliased(HragEntity)
        object_entity = aliased(HragEntity)
        evidence_rows = db.session.execute(
            db.select(HragRelationEvidence, HragRelation, subject_entity, object_entity)
            .join(HragRelation, HragRelationEvidence.relation_id == HragRelation.id)
            .join(subject_entity, HragRelation.subject_id == subject_entity.id)
            .join(object_entity, HragRelation.object_id == object_entity.id)
            .where(HragRelationEvidence.news_item_id.in_(news_item_ids))
        ).all()
        graph_facts = [
            {
                "id": f"relation:{evidence.id}",
                "source": f"news-item:{evidence.news_item_id}",
                "fact": f"{subject.name} -[{relation.predicate}]-> {object_.name}",
            }
            for evidence, relation, subject, object_ in evidence_rows
        ]
        return {"passages": passages, "graph_facts": graph_facts}

    @staticmethod
    def _cosine_distance(left: list[float], right: list[float]) -> float:
        if len(left) != len(right):
            return 1.0
        left_norm = sum(value * value for value in left) ** 0.5
        right_norm = sum(value * value for value in right) ** 0.5
        if not left_norm or not right_norm:
            return 1.0
        return 1 - sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True)) / (left_norm * right_norm)


class HragAge:
    graph_name = "hrag"
    _parameter_pattern = re.compile(r"\$([A-Za-z][A-Za-z0-9_]*)")
    _forbidden_keywords = re.compile(r"\b(CALL|CREATE|DELETE|DETACH|DROP|FOREACH|LOAD|MERGE|REMOVE|SET)\b", re.IGNORECASE)

    @classmethod
    def sync(cls) -> None:
        if db.engine.dialect.name != "postgresql":
            return
        try:
            cls._load()
            exists = db.session.execute(text("SELECT 1 FROM ag_catalog.ag_graph WHERE name = :name"), {"name": cls.graph_name}).scalar()
            if not exists:
                db.session.execute(text("SELECT ag_catalog.create_graph(:name)"), {"name": cls.graph_name})
                db.session.commit()
            for entity in db.session.execute(db.select(HragEntity)).scalars():
                cls._cypher(
                    f"MERGE (n:{entity.entity_type} {{entity_id: {cls._literal(entity.id)}}}) "
                    f"SET n.name = {cls._literal(entity.name)}, n.schema_version = {cls._literal(entity.schema_version)} RETURN n"
                )
            for relation in db.session.execute(db.select(HragRelation)).scalars():
                cls._cypher(
                    f"MATCH (source {{entity_id: {cls._literal(relation.subject_id)}}}), "
                    f"(target {{entity_id: {cls._literal(relation.object_id)}}}) "
                    f"MERGE (source)-[edge:{relation.predicate} {{relation_id: {cls._literal(relation.id)}}}]->(target) "
                    f"SET edge.schema_version = {cls._literal(relation.schema_version)} RETURN edge"
                )
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Failed to synchronize HRAG data to Apache AGE")

    @classmethod
    def query(cls, cypher: str, parameters: dict[str, Any]) -> list[str]:
        if db.engine.dialect.name != "postgresql":
            raise RuntimeError("Apache AGE requires PostgreSQL")
        cls._validate_read_only_query(cypher, parameters)
        cls._load()
        statement = cls._parameter_pattern.sub(lambda match: cls._literal(parameters[match.group(1)]), cypher)
        return [str(row[0]) for row in cls._cypher(statement)]

    @classmethod
    def _validate_read_only_query(cls, cypher: str, parameters: dict[str, Any]) -> None:
        normalized = cypher.strip()
        if not normalized or ";" in normalized or "//" in normalized or "/*" in normalized:
            raise ValueError("Cypher must be a single statement without comments")
        if cls._forbidden_keywords.search(normalized):
            raise ValueError("Cypher must be read-only")
        if not re.search(r"\bRETURN\b", normalized, re.IGNORECASE):
            raise ValueError("Cypher must include RETURN")
        if not re.search(r"\bAS\s+result\s*$", normalized, re.IGNORECASE):
            raise ValueError("Cypher must return exactly one value aliased as result")
        missing = sorted(set(cls._parameter_pattern.findall(normalized)) - set(parameters))
        if missing:
            raise ValueError("Cypher is missing parameters: " + ", ".join(missing))

    @classmethod
    def _load(cls) -> None:
        db.session.execute(text("LOAD 'age'"))
        db.session.execute(text('SET search_path = ag_catalog, "$user", public'))

    @classmethod
    def _cypher(cls, cypher: str):
        return db.session.execute(
            text(f"SELECT * FROM ag_catalog.cypher('{cls.graph_name}', {cls._dollar_quote(cypher)}) AS (result agtype)")
        ).all()

    @staticmethod
    def _dollar_quote(value: str) -> str:
        tag = "hrag"
        suffix = 0
        while f"${tag}$" in value:
            suffix += 1
            tag = f"hrag_{suffix}"
        return f"${tag}${value}${tag}$"

    @staticmethod
    def _literal(value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, list):
            return "[" + ", ".join(HragAge._literal(item) for item in value) + "]"
        if isinstance(value, dict):
            if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", str(key)) for key in value):
                raise ValueError("Cypher map parameter keys must be identifiers")
            return "{" + ", ".join(f"{key}: {HragAge._literal(item)}" for key, item in value.items()) + "}"
        return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"
