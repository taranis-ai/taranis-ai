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
    inference = AsyncMock(return_value={"output_text": '{"entities": [], "relations": []}'})
    monkeypatch.setattr("llm_bot.client.LLMClient.create_response", inference)
    index_item("test-work")
    assert submitted.last_request.json()["extraction"] == {"entities": [], "relations": []}
    assert inference.await_count == 1
    assert content in inference.call_args.args[1]
    requests_mock.post(route, json={**job, "cached_result": {"entities": [], "relations": []}})
    index_item("test-work")
    assert inference.await_count == 1
    requests_mock.post(
        route, json={**job, "pipeline": "embedding", "dimensions": 3, "endpoint": {**job["endpoint"], "api_format": "embeddings"}}
    )
    monkeypatch.setattr("llm_bot.embedding_client.EmbeddingClient.create_embedding", AsyncMock(return_value=[float("nan"), 1, 0]))
    with pytest.raises(RuntimeError, match="^HRAG indexing failed; retry scheduled$"):
        index_item("test-work")
    assert submitted.last_request.json()["failed"] is True
    assert "NaN" not in submitted.last_request.text
