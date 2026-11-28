"""Use llm-bot embedding contracts through the task's pooled HTTP transport."""

from llm_bot.embedding_client import EmbeddingClient
from models.llm import EmbeddingDimensionMismatch

from worker.http_client import http_request


def create_embeddings(texts: str | list[str], endpoint: dict, dimensions: int | None = None) -> list[list[float]]:
    client = EmbeddingClient(
        base_url=endpoint["base_url"],
        api_key=endpoint.get("api_key", ""),
        model=endpoint.get("model", ""),
        timeout=endpoint["timeout"],
    )
    response = http_request(
        "POST",
        f"{client.base_url}{client.path}",
        json=client.build_request(texts, dimensions=endpoint.get("dimensions")),
        headers={"Authorization": f"Bearer {client.api_key}"} if client.api_key else {},
        timeout=endpoint["timeout"],
        verify=True,
    )
    response.raise_for_status()
    vectors = client.parse_response(response.json(), count=1 if isinstance(texts, str) else len(texts))
    if dimensions is not None and any(len(vector) != dimensions for vector in vectors):
        raise EmbeddingDimensionMismatch(EmbeddingDimensionMismatch.public_message)
    return vectors


def create_embedding(text: str, endpoint: dict, dimensions: int | None = None) -> list[float]:
    return create_embeddings(text, endpoint, dimensions)[0]
