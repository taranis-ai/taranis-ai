import json
from unittest.mock import AsyncMock

import pytest

from worker.config import Config
from worker.hrag import index_item


def test_worker_claim_extraction_and_cached_retry(requests_mock, monkeypatch):
    route = f"{Config.TARANIS_CORE_URL}/worker/hrag/work/test-work"
    content = "Acme did not attack Beta."
    job = {
        "id": "test-work",
        "token": "lease",
        "fingerprint": "a" * 64,
        "pipeline": "extraction",
        "content": content,
        "endpoint": {"name": "extract", "base_url": "https://provider.invalid/v1", "api_format": "responses"},
        "verification_endpoint": {"name": "verify", "base_url": "https://verify.invalid/v1/systemone", "api_format": "systemone"},
        "reasoning_effort": "none",
        "dimensions": 0,
    }
    requests_mock.post(route, json=job)
    submitted = requests_mock.put(route, json={"message": "accepted"})
    compact = {
        "entities": [{"id": "a", "name": "Acme", "type": "ORG"}, {"id": "b", "name": "Beta", "type": "ORG"}],
        "relations": [
            {"source_id": "a", "target_id": "b", "type": "ATTACKS", "quote": content, "assertion": "affirmed"},
            {"source_id": "a", "target_id": "b", "type": "OWNS", "quote": content, "assertion": "affirmed"},
            {"source_id": "a", "target_id": "b", "type": "USES", "quote": content, "assertion": "affirmed"},
        ],
    }
    invalid = {**compact, "entities": [{**compact["entities"][0], "name": "Absent"}, compact["entities"][1]]}
    inference = AsyncMock(side_effect=[{"output_text": json.dumps(invalid)}, {"output_text": json.dumps(compact)}])
    monkeypatch.setattr("llm_bot.client.LLMClient.create_response", inference)
    verification = AsyncMock(
        return_value={
            "relation_0": {"affirmed": 0.0, "negated": 1.0, "uncertain": 0.0, "not_stated": 0.0},
            "relation_1": {"affirmed": 0.0, "negated": 0.0, "uncertain": 0.0, "not_stated": 1.0},
        }
    )
    monkeypatch.setattr("llm_bot.decisions_client.DecisionsClient.create_decision", verification)
    index_item("test-work")
    stored = submitted.last_request.json()["extraction"]
    assert stored["entities"][0]["evidence"] == {"start": 0, "end": 4, "quote": "Acme"}
    assert stored["relations"][0]["evidence"] == {"start": 0, "end": len(content), "quote": content}
    assert stored["relations"][0]["assertion"] == "negated"
    assert len(stored["relations"]) == 1
    assert verification.await_count == 1
    assert set(verification.call_args.args[1]) == {"relation_0", "relation_1"}
    assert inference.await_count == 2
    assert content in inference.call_args_list[0].args[1]
    requests_mock.post(route, json={**job, "cached_result": stored})
    index_item("test-work")
    assert inference.await_count == 2
    requests_mock.post(
        route,
        json={
            **job,
            "pipeline": "embedding",
            "dimensions": 3,
            "endpoint": {**job["endpoint"], "api_format": "embeddings"},
            "chunks": [{"start": 0, "end": len(content)}],
        },
    )
    embedding = requests_mock.post("https://provider.invalid/v1/embeddings", json={"data": [{"embedding": [1, 0, 0]}]})
    index_item("test-work")
    assert embedding.last_request.json() == {"input": [content], "encoding_format": "float", "dimensions": 3}
    assert submitted.last_request.json()["chunks"] == [{"start": 0, "end": len(content), "embedding": [1, 0, 0]}]
    for vector in ([1, 0], [float("nan"), 1, 0]):
        requests_mock.post("https://provider.invalid/v1/embeddings", json={"data": [{"embedding": vector}]})
        with pytest.raises(RuntimeError, match="^HRAG indexing failed; retry scheduled$"):
            index_item("test-work")
        assert submitted.last_request.json()["failed"] is True
        assert "NaN" not in submitted.last_request.text
    requests_mock.post(
        route,
        json={
            **job,
            "pipeline": "embedding",
            "dimensions": 3,
            "endpoint": {**job["endpoint"], "api_format": "embeddings"},
            "chunks": [{"start": 0, "end": 4}, {"start": 5, "end": len(content)}],
        },
    )
    embedding = requests_mock.post(
        "https://provider.invalid/v1/embeddings", json={"data": [{"index": 1, "embedding": [0, 1, 0]}, {"index": 0, "embedding": [1, 0, 0]}]}
    )
    index_item("test-work")
    assert embedding.last_request.json()["input"] == ["Acme", "did not attack Beta."]
    assert submitted.last_request.json()["chunks"] == [
        {"start": 0, "end": 4, "embedding": [1, 0, 0]},
        {"start": 5, "end": len(content), "embedding": [0, 1, 0]},
    ]
    requests_mock.post(route, json=job)
    inference.side_effect = None
    inference.return_value = {"output_text": json.dumps(compact)}
    verification.side_effect = RuntimeError("private verification failure")
    with pytest.raises(RuntimeError, match="^HRAG indexing failed; retry scheduled$"):
        index_item("test-work")
    assert submitted.last_request.json()["failed"] is True
    assert submitted.last_request.json()["extraction"] is None
