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
        "dimensions": 0,
    }
    requests_mock.post(route, json=job)
    submitted = requests_mock.put(route, json={"message": "accepted"})
    compact = {
        "entities": [{"id": "a", "name": "Acme", "type": "ORG"}, {"id": "b", "name": "Beta", "type": "ORG"}],
        "relations": [{"source_id": "a", "target_id": "b", "type": "ATTACKS", "quote": content, "assertion": "negated"}],
    }
    invalid = {**compact, "relations": [{**compact["relations"][0], "quote": "Acme attacked Beta."}]}
    inference = AsyncMock(side_effect=[{"output_text": json.dumps(invalid)}, {"output_text": json.dumps(compact)}])
    monkeypatch.setattr("llm_bot.client.LLMClient.create_response", inference)
    index_item("test-work")
    stored = submitted.last_request.json()["extraction"]
    assert stored["entities"][0]["evidence"] == {"start": 0, "end": 4, "quote": "Acme"}
    assert stored["relations"][0]["evidence"] == {"start": 0, "end": len(content), "quote": content}
    assert stored["relations"][0]["assertion"] == "negated"
    assert inference.await_count == 2
    assert content in inference.call_args_list[0].args[1]
    requests_mock.post(route, json={**job, "cached_result": stored})
    index_item("test-work")
    assert inference.await_count == 2
    requests_mock.post(
        route, json={**job, "pipeline": "embedding", "dimensions": 3, "endpoint": {**job["endpoint"], "api_format": "embeddings"}}
    )
    embedding = requests_mock.post("https://provider.invalid/v1/embeddings", json={"data": [{"embedding": [1, 0, 0]}]})
    index_item("test-work")
    assert embedding.last_request.json() == {"input": content, "model": "", "dimensions": 3}
    assert submitted.last_request.json()["vector"]["embedding"] == [1, 0, 0]
    for vector in ([1, 0], [float("nan"), 1, 0]):
        requests_mock.post("https://provider.invalid/v1/embeddings", json={"data": [{"embedding": vector}]})
        with pytest.raises(RuntimeError, match="^HRAG indexing failed; retry scheduled$"):
            index_item("test-work")
        assert submitted.last_request.json()["failed"] is True
        assert "NaN" not in submitted.last_request.text
