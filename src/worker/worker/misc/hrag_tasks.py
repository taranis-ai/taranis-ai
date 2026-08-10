from typing import Any

from rq import get_current_job

from worker.bot_api import BotApi
from worker.config import Config
from worker.core_api import CoreApi, build_failure_task_result, build_success_task_result


def hrag_query_task(question: str, bot_id: str):
    job = get_current_job()
    core_api = CoreApi()
    task_id = job.id if job else "hrag_query"
    try:
        config = core_api.get_bot_config(bot_id) or {}
        parameters = config.get("parameters") or {}
        client = BotApi(
            bot_endpoint=str(parameters.get("BOT_ENDPOINT") or "").rstrip("/"),
            bot_api_key=parameters.get("BOT_API_KEY") or Config.BOT_API_KEY,
            requests_timeout=parameters.get("REQUESTS_TIMEOUT"),
        )
        embedding = client.api_post("/embed", {"text": question}) or {}
        vector = embedding.get("embedding")
        if not isinstance(vector, list) or not vector:
            raise RuntimeError("LLM bot returned no query embedding")
        user_id = str((job.meta or {}).get("user_id") or "") if job else ""
        if not user_id:
            raise RuntimeError("HRAG query has no user context")
        retrieval = core_api.retrieve_hrag(vector, user_id) or {"passages": [], "graph_facts": []}
        schema = core_api.get_hrag_schema() or {}
        graph_query = client.api_post(
            "/graph-query-generation", {"question": question, "graph_name": "hrag", "schema": _graph_schema(schema)}
        )
        if isinstance(graph_query, dict):
            graph_rows = core_api.query_hrag_graph(graph_query.get("cypher", ""), graph_query.get("parameters", {}), user_id) or {"rows": []}
            retrieval["graph_facts"].extend(
                {"id": f"graph:{index}", "source": "graph://hrag", "fact": row} for index, row in enumerate(graph_rows.get("rows", []))
            )
        answer = client.api_post("/hrag", _hrag_request(question, retrieval))
        if not isinstance(answer, dict):
            raise RuntimeError("LLM bot returned no HRAG answer")
        result = {"answer": answer, "graph_query": graph_query, "retrieval": retrieval}
        core_api.save_task_result(
            task_id,
            "hrag_query_task",
            "SUCCESS",
            worker_id=bot_id,
            worker_type="HRAG_QUERY",
            result=build_success_task_result(default_message="HRAG answer generated", output=result),
        )
        return result
    except Exception as exc:
        core_api.save_task_result(
            task_id,
            "hrag_query_task",
            "FAILURE",
            worker_id=bot_id,
            worker_type="HRAG_QUERY",
            result=build_failure_task_result("HRAG query failed", reason="hrag_query_failed", data={"error": str(exc)}),
        )
        raise


def _graph_schema(schema: dict[str, Any]) -> dict[str, Any]:
    entity_types = schema.get("entity_types") or []
    relation_types = schema.get("relation_types") or []
    return {
        "node_labels": [{"label": item["name"], "properties": [{"name": "name", "type": "string"}]} for item in entity_types],
        "relationship_types": [
            {"type": item["name"], "source_labels": item["source_types"], "target_labels": item["target_types"], "properties": []}
            for item in relation_types
        ],
        "default_limit": 20,
        "maximum_limit": 100,
    }


def _hrag_request(question: str, retrieval: dict[str, Any]) -> dict[str, Any]:
    return {
        "question": question,
        "passages": [{"id": item["id"], "source": item["source"], "text": item["text"]} for item in retrieval.get("passages", [])],
        "graph_facts": [{"id": item["id"], "source": item["source"], "fact": item["fact"]} for item in retrieval.get("graph_facts", [])],
    }
