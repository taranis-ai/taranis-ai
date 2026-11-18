from time import monotonic

import requests
from models.llm import OPENROUTER_DECISIONS_URL, LLMAPIFormat, LLMProcessingMode
from models.llm_catalog import LLMModelCatalogQuery, LLMModelSuggestion, OpenRouterCatalog

from core.log import logger


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_INFERENCE_PATHS = {
    (OPENROUTER_BASE_URL, "responses"): "/api/v1/responses",
    (OPENROUTER_BASE_URL, "chat_completions"): "/api/v1/chat/completions",
    (OPENROUTER_DECISIONS_URL, "systemone"): "/api/alpha/decisions",
}
CATALOG_MAX_BYTES = 4 * 1024 * 1024
_openrouter_cache: tuple[float, OpenRouterCatalog | None] = (0, None)


def _fetch_openrouter_catalog() -> OpenRouterCatalog:
    with requests.get(
        f"{OPENROUTER_BASE_URL}/models",
        params={"output_modalities": "text,decisions"},
        timeout=(2, 3),
        allow_redirects=False,
        stream=True,
    ) as response:
        if response.status_code != 200:
            raise requests.HTTPError(f"Unexpected OpenRouter catalog status: {response.status_code}")
        body = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            body.extend(chunk)
            if len(body) > CATALOG_MAX_BYTES:
                raise ValueError("OpenRouter catalog exceeds response size limit")
    return OpenRouterCatalog.model_validate_json(body)


def _openrouter_models(base_url: str, api_format: LLMAPIFormat, processing_mode: LLMProcessingMode) -> list[LLMModelSuggestion]:
    global _openrouter_cache
    if not (path := OPENROUTER_INFERENCE_PATHS.get((base_url, api_format))):
        return []
    if processing_mode == "openrouter_batch" and api_format != "systemone":
        path = "/api/v1/batches"

    expires_at, catalog = _openrouter_cache
    if monotonic() >= expires_at:
        try:
            catalog = _fetch_openrouter_catalog()
            _openrouter_cache = (monotonic() + 300, catalog)
        except (requests.RequestException, ValueError):
            logger.exception("Failed to retrieve the OpenRouter model catalog")
            catalog = None
            _openrouter_cache = (monotonic() + 15, None)

    return [LLMModelSuggestion(id=model.id, name=model.name) for model in catalog.data if path in model.endpoints] if catalog else []


CATALOG_PROVIDERS = {OPENROUTER_BASE_URL: _openrouter_models, OPENROUTER_DECISIONS_URL: _openrouter_models}


def get_model_suggestions(query: LLMModelCatalogQuery) -> dict[LLMAPIFormat, list[LLMModelSuggestion]]:
    suggestions = {}
    for api_format, base_url in query.api_urls.items():
        base_url = base_url.rstrip("/")
        if provider := CATALOG_PROVIDERS.get(base_url):
            suggestions[api_format] = provider(base_url, api_format, query.processing_mode)
    return suggestions
