"""Use llm-bot embedding contracts through the task's pooled HTTP transport."""

from llm_bot.embedding_client import EmbeddingClient

from worker.http_client import http_request


def create_embedding(text: str, endpoint: dict, dimensions: int | None = None) -> list[float]:
    client = EmbeddingClient(
        base_url=endpoint["base_url"],
        api_key=endpoint.get("api_key", ""),
        model=endpoint.get("model", ""),
        timeout=endpoint["timeout"],
    )
    response = http_request(
        "POST",
        f"{client.base_url}{client.path}",
        json=client.build_request(text, dimensions=dimensions),
        headers={"Authorization": f"Bearer {client.api_key}"} if client.api_key else {},
        timeout=endpoint["timeout"],
        verify=True,
    )
    response.raise_for_status()
    return client.parse_response(response.json(), dimensions=dimensions)[0]
