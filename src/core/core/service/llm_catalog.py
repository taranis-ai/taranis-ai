import asyncio
from threading import Lock
from time import monotonic

from models.llm import OPENROUTER_DECISIONS_URL, LLMAPIFormat, LLMProcessingMode
from models.llm_catalog import LLMModelCatalogQuery, LLMModelSuggestion, OpenRouterCatalog
from niquests import AsyncSession, RequestException

from core.log import logger


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_INFERENCE_PATHS = {
    (OPENROUTER_BASE_URL, "responses"): "/api/v1/responses",
    (OPENROUTER_BASE_URL, "chat_completions"): "/api/v1/chat/completions",
    (OPENROUTER_DECISIONS_URL, "systemone"): "/api/alpha/decisions",
}
CATALOG_TIMEOUT_SECONDS = 5
_openrouter_cache: tuple[float, OpenRouterCatalog | None] = (0, None)
_openrouter_cache_lock = Lock()


async def _fetch_openrouter_catalog() -> OpenRouterCatalog:
    async with asyncio.timeout(CATALOG_TIMEOUT_SECONDS), AsyncSession() as session:
        response = await session.get(
            f"{OPENROUTER_BASE_URL}/models",
            params={"output_modalities": "text,decisions"},
        )
        response.raise_for_status()
        return OpenRouterCatalog.model_validate_json(response.content or b"")


def _get_openrouter_catalog() -> OpenRouterCatalog | None:
    global _openrouter_cache
    with _openrouter_cache_lock:
        expires_at, catalog = _openrouter_cache
        if monotonic() < expires_at:
            return catalog
        try:
            catalog = asyncio.run(_fetch_openrouter_catalog())
            _openrouter_cache = (monotonic() + 300, catalog)
        except (RequestException, TimeoutError, ValueError):
            logger.exception("Failed to retrieve the OpenRouter model catalog")
            catalog = None
            _openrouter_cache = (monotonic() + 15, None)
        return catalog


def _openrouter_models(api_urls: dict[LLMAPIFormat, str], processing_mode: LLMProcessingMode) -> dict[LLMAPIFormat, list[LLMModelSuggestion]]:
    paths = {api_format: OPENROUTER_INFERENCE_PATHS.get((base_url, api_format)) for api_format, base_url in api_urls.items()}
    catalog = _get_openrouter_catalog() if any(paths.values()) else None
    suggestions = {}
    for api_format, path in paths.items():
        if path and processing_mode == "openrouter_batch" and api_format != "systemone":
            path = "/api/v1/batches"
        suggestions[api_format] = (
            [LLMModelSuggestion(id=model.id, name=model.name) for model in catalog.data if path in model.endpoints]
            if catalog and path
            else []
        )
    return suggestions


CATALOG_PROVIDERS = {OPENROUTER_BASE_URL: _openrouter_models, OPENROUTER_DECISIONS_URL: _openrouter_models}


def get_model_suggestions(query: LLMModelCatalogQuery) -> dict[LLMAPIFormat, list[LLMModelSuggestion]]:
    provider_urls = {}
    for api_format, base_url in query.api_urls.items():
        base_url = base_url.rstrip("/")
        if provider := CATALOG_PROVIDERS.get(base_url):
            provider_urls.setdefault(provider, {})[api_format] = base_url
    suggestions = {}
    for provider, api_urls in provider_urls.items():
        suggestions.update(provider(api_urls, query.processing_mode))
    return suggestions
