"""Retrieval over current, authorized evidence; no provider-generated query code."""

import asyncio
import time

from llm_bot.tasks.evidence import prepare_retrieval_plan
from models.hrag import EmbeddingResult, EvidenceReference, ExtractionResult, GraphPlan, HragResult, RetrievalEvidence, bounded_content
from sqlalchemy import select
from sqlalchemy.orm import defer

from core.config import Config
from core.log import logger
from core.managers.db_manager import db
from core.model.hrag import HragGeneration, HragWork
from core.model.news_item import NewsItem
from core.model.settings import Settings
from core.model.story import Story
from core.model.user import User
from core.service.hrag.indexing import fingerprint, generation_endpoint
from core.service.hrag.stores import graph_search, vector_search


LIMIT_NOTICE = (
    "Evidence covers currently accessible indexed content only. Retrieval limits and unresolved names prevent complete corpus counts."
)


class PlanningClient:
    """Adapt the existing deadline-aware Chat transport to the library task API."""

    def __init__(self, endpoint: dict, deadline: float):
        self.endpoint = endpoint
        self.deadline = deadline

    async def create_response(self, system_input: str, user_input: str, response_format: dict | None = None) -> dict:
        client = endpoint_client(self.endpoint, self.deadline)
        return client.create_response(
            [{"role": "user", "content": user_input}], lambda _delta: None, prompt=system_input, response_format=response_format
        )


def endpoint_client(endpoint: dict, deadline: float):
    from core.service.chat import ChatClient

    settings = Settings.with_defaults({"llm_endpoints": {"hrag": endpoint}, "llm_chat_endpoint": "hrag"})
    # An embedding transport cannot resolve as Chat; initialize with a compatible
    # format and then select its fixed, non-generative route below.
    return ChatClient(settings, deadline=deadline)


def query_embedding(question: str, endpoint: dict, deadline: float) -> EmbeddingResult:
    client = endpoint_client({**endpoint, "api_format": "responses"}, deadline)
    client.endpoint = "embeddings"
    payload = {"input": question}
    if endpoint["model"]:
        payload["model"] = endpoint["model"]
    with client._response(payload) as response:
        response.raise_for_status()
        return EmbeddingResult(embedding=response.json()["data"][0]["embedding"])


def run_inference(coroutine, deadline: float):
    async def bounded():
        return await asyncio.wait_for(coroutine, timeout=max(0.001, deadline - time.monotonic()))

    return asyncio.run(bounded())


def iter_authorized_work(user: User, pipeline: str | None = None, filters: dict | None = None, ids: list[str] | None = None):
    """Apply ACL, story/item TLP and live content checks before ranking or limits."""
    story_query = Story.visible_query(user, Story.get_filter_query({**(filters or {}), "_user": user})).with_only_columns(Story.id)
    query = (
        select(HragWork, HragGeneration, NewsItem)
        .join(HragGeneration, HragGeneration.id == HragWork.generation_id)
        .join(NewsItem, NewsItem.id == HragWork.news_item_id)
        .where(HragGeneration.active, HragWork.status == "ready", NewsItem.story_id.in_(story_query))
    )
    if pipeline:
        query = query.where(HragGeneration.pipeline == pipeline)
    if ids is not None:
        query = query.where(HragWork.id.in_(ids))
    accessible_tlps = user.get_highest_tlp().get_accessible_levels()
    query = query.options(defer(HragWork.result)).execution_options(yield_per=200)
    for work, generation, item in db.session.execute(query):
        if (
            item.tlp_level.value in accessible_tlps
            and item.allowed_with_acl(user, require_write_access=False)
            and item.story
            and item.story.tlp_level.value in accessible_tlps
            and bool(bounded_content(item.content, generation.config["limit"]).strip())
            and work.fingerprint == fingerprint(item, generation)
        ):
            yield work, generation, item


def authorized_work(user: User, pipeline: str | None = None, filters: dict | None = None, ids: list[str] | None = None) -> dict[str, tuple]:
    return {work.id: (work, generation, item) for work, generation, item in iter_authorized_work(user, pipeline, filters, ids)}


def evidence_from_reference(reference: EvidenceReference, authorized: dict[str, tuple]) -> RetrievalEvidence | None:
    record = authorized.get(reference.work_id)
    if not record:
        return None
    work, generation, item = record
    if reference.fingerprint != work.fingerprint:
        return None
    for key in reference.support_ids:
        support_id, _, expected = key.partition(":")
        support = authorized.get(support_id)
        if not support or support[0].fingerprint != expected:
            return None
    branch = "graph" if generation.pipeline == "extraction" else "vector"
    content = bounded_content(item.content, generation.config["limit"])
    quote, assertion, description = content, None, ""
    if branch == "graph":
        result = ExtractionResult.model_validate(work.result).validate_content(content)
        if reference.relation_index is not None:
            if reference.relation_index >= len(result.relations):
                return None
            relation = result.relations[reference.relation_index]
            entities = {entity.id: entity for entity in result.entities}
            quote, assertion = relation.evidence.quote, relation.assertion
            description = f"{entities[relation.source_id].name} — {relation.type} → {entities[relation.target_id].name}"
            if relation.date:
                description += f" ({relation.date})"
        else:
            quote = "\n".join(dict.fromkeys(entity.evidence.quote for entity in result.entities))
        if not quote:
            return None
    return RetrievalEvidence(
        **reference.model_dump(),
        branch=branch,
        news_item_id=item.id,
        story_id=item.story_id,
        title=item.title,
        quote=quote,
        description=description,
        assertion=assertion,
        truncated=len(item.content or "") > generation.config["limit"],
    )


def reauthorize(references: list[EvidenceReference], user_id: str, filters: dict | None = None) -> list[RetrievalEvidence]:
    db.session.rollback()
    user = db.session.get(User, user_id)
    if not user or "ASSESS_ACCESS" not in user.get_permissions():
        return []
    ids = list(
        {reference.work_id for reference in references} | {key.partition(":")[0] for reference in references for key in reference.support_ids}
    )
    authorized = authorized_work(user, filters=filters, ids=ids)
    result = [evidence for reference in references if (evidence := evidence_from_reference(reference, authorized))]
    db.session.rollback()
    return result


def retrieve(context: dict, user_id: str, settings: dict, deadline: float, stream) -> HragResult:
    from core.service.chat import ChatProviderError, ChatService, ChatUnavailableError

    if not Config.HRAG_ENABLED:
        raise ChatUnavailableError("HRAG is disabled")
    result = HragResult(notices=[LIMIT_NOTICE])
    plan = GraphPlan()
    plan_ok = False
    graph_ok = False
    vector_ok = False
    try:
        endpoint = Settings.get_llm_endpoint("graph_planning", settings)
        if not endpoint or endpoint["processing_mode"] != "realtime":
            raise ValueError("Graph planning endpoint unavailable")
        client = PlanningClient(endpoint, deadline)
        db.session.rollback()
        plan = run_inference(prepare_retrieval_plan(context, GraphPlan).run(client), deadline)
        filters = ChatService._search_filters(
            plan.filters.model_dump_json(exclude_defaults=True),
            context["available_filters"],
            {item["id"] for item in context["recent_results"]},
        )
        result.filters = ChatService._query_params(filters, context["analyst_timezone"])
        plan_ok = True
        stream.stage("searching")
        user = db.session.get(User, user_id)
        if user is None:
            raise ValueError("User unavailable")
        if not db.session.scalar(db.select(HragGeneration.id).where(HragGeneration.active, HragGeneration.pipeline == "extraction")):
            raise ValueError("Graph generation unavailable")
        keys = [work.graph_key for work, _, _ in iter_authorized_work(user, "extraction", result.filters)]
        db.session.rollback()
        paths = graph_search(plan, keys, min(50, max(1, Config.HRAG_GRAPH_LIMIT)), max(0.001, min(30, deadline - time.monotonic())))
        references = []
        seen = set()
        for path_number, path in enumerate(paths, start=1):
            supports = list(dict.fromkeys(row["key"] for row in path))
            additions = []
            for row in path:
                identity = (row["key"], row["idx"], tuple(supports))
                if identity in seen:
                    continue
                seen.add(identity)
                additions.append(
                    EvidenceReference(
                        citation=f"G{len(references) + len(additions) + 1}",
                        work_id=row["work_id"],
                        fingerprint=row["key"].partition(":")[2],
                        support_ids=supports,
                        relation_index=row["idx"],
                        path_id=path_number,
                    )
                )
            if len(references) + len(additions) > min(50, max(1, Config.HRAG_GRAPH_LIMIT)):
                break
            references.extend(additions)
        result.evidence.extend(reauthorize(references, user_id, result.filters))
        graph_ok = True
    except Exception:
        db.session.rollback()
        logger.exception("HRAG graph retrieval failed")
        result.notices.append(
            "Graph retrieval is unavailable; the answer uses vector evidence where available."
            if plan_ok
            else "Graph planning is unavailable; vector matching could not apply inferred Assess filters."
        )
    try:
        generation = db.session.scalar(db.select(HragGeneration).where(HragGeneration.active, HragGeneration.pipeline == "embedding"))
        if generation is None or not (endpoint := generation_endpoint(generation)):
            raise ValueError("Embedding generation unavailable")
        dimensions = generation.config["dimensions"]
        embedding_generation_id = generation.id
        db.session.rollback()
        vector = query_embedding(context["latest_message"], endpoint, deadline)
        if len(vector.embedding) != dimensions:
            raise ValueError("Unexpected embedding dimensions")
        user = db.session.get(User, user_id)
        if user is None:
            raise ValueError("User unavailable")
        authorized = {
            work.id: (work.fingerprint, generation.id) for work, generation, _ in iter_authorized_work(user, "embedding", result.filters)
        }
        if any(generation_id != embedding_generation_id for _, generation_id in authorized.values()):
            raise ValueError("Embedding generation changed during retrieval")
        work_ids = vector_search(vector.embedding, list(authorized), min(100, max(1, Config.HRAG_VECTOR_LIMIT)))
        references = [
            EvidenceReference(citation=f"V{index + 1}", work_id=work_id, fingerprint=authorized[work_id][0])
            for index, work_id in enumerate(work_ids)
        ]
        result.evidence.extend(reauthorize(references, user_id, result.filters))
        vector_ok = True
    except Exception:
        db.session.rollback()
        logger.exception("HRAG vector retrieval failed")
        result.notices.append("Vector retrieval is unavailable; the answer uses graph evidence where available.")
    if not graph_ok and not vector_ok:
        raise ChatProviderError("HRAG retrieval failed")
    return result


def reference_metadata(result: HragResult) -> dict:
    return {
        "references": [
            EvidenceReference.model_validate(e.model_dump(include=set(EvidenceReference.model_fields))).model_dump() for e in result.evidence
        ],
        "notices": result.notices,
        "filters": result.filters,
    }


def display_result(metadata: dict, user_id: str) -> HragResult:
    references = [EvidenceReference.model_validate(value) for value in metadata.get("references", [])]
    evidence = reauthorize(references, user_id, metadata.get("filters"))
    notices = list(metadata.get("notices", []))
    if len(evidence) < len(references):
        notices.append("Some evidence is no longer available or has changed.")
    return HragResult(evidence=evidence, notices=notices, filters=metadata.get("filters", {}))
