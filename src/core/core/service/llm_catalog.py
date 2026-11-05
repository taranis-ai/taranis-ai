"""Server-side model discovery for named LLM providers.

The browser never receives the provider API key: Core reads it from the saved
endpoint (or accepts it once from the authenticated admin form), calls the
provider catalogue, and returns only minimal model metadata.
"""

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests
from models.llm import (
    ORCAROUTER_DEFAULT_BASE_URL,
    ORCAROUTER_DEFAULT_MODEL,
    ORCAROUTER_FALLBACK_MODELS,
    ORCAROUTER_PROVIDER_ID,
    filter_catalog_models,
)

from core.log import logger


CATALOG_TIMEOUT_SECONDS = 10
CATALOG_MAX_BYTES = 2 * 1024 * 1024
CATALOG_MAX_ITEMS = 2000
CATALOG_CACHE_SECONDS = 300
CATALOG_CACHE_MAX_ENTRIES = 16
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
SUPPORTED_API_FORMATS = {"responses": "chat", "chat_completions": "chat"}
_FALLBACK_BY_ID = {model["id"]: model for model in ORCAROUTER_FALLBACK_MODELS}


class CatalogError(Exception):
    code = "catalog_unavailable"
    public_message = "The OrcaRouter model catalogue is temporarily unavailable."
    status = 502


class CatalogAuthError(CatalogError):
    code = "catalog_auth_failed"
    public_message = "OrcaRouter rejected this API key. Check the key or create a new one in the OrcaRouter console."
    status = 401


class CatalogRequestError(CatalogError):
    code = "catalog_invalid_request"
    public_message = "Enter a valid OrcaRouter API base URL."
    status = 400


@dataclass(frozen=True)
class CatalogResult:
    models: list[dict[str, Any]]
    source: str
    cached: bool = False


_cache: dict[tuple[str, str, str, str, tuple[str, ...]], tuple[float, list[dict[str, Any]]]] = {}
_cache_lock = threading.Lock()


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _validate_base_url(base_url: str) -> str:
    value = (base_url or "").strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username or parsed.password:
        raise CatalogRequestError
    if parsed.query or parsed.fragment:
        raise CatalogRequestError
    if parsed.scheme != "https" and parsed.hostname not in LOOPBACK_HOSTS:
        raise CatalogRequestError
    return value


def _catalog_url(base_url: str) -> str:
    return f"{_validate_base_url(base_url)}/models"


def _cache_key(
    base_url: str, api_key: str, api_format: str, capability: str, required_input_modalities: tuple[str, ...]
) -> tuple[str, str, str, str, tuple[str, ...]]:
    key_digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16] if api_key else "anonymous"
    return (base_url, key_digest, api_format, capability, required_input_modalities)


def _read_cached(key: tuple[str, str, str, str, tuple[str, ...]]) -> list[dict[str, Any]] | None:
    with _cache_lock:
        cached = _cache.get(key)
        if cached is None:
            return None
        created_at, models = cached
        if time.monotonic() - created_at > CATALOG_CACHE_SECONDS:
            _cache.pop(key, None)
            return None
        return models


def _write_cache(key: tuple[str, str, str, str, tuple[str, ...]], models: list[dict[str, Any]]) -> None:
    with _cache_lock:
        while len(_cache) >= CATALOG_CACHE_MAX_ENTRIES:
            _cache.pop(next(iter(_cache)))
        _cache[key] = (time.monotonic(), models)


def _download(url: str, api_key: str, capability: str) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        with requests.get(
            url,
            headers=headers,
            params={"capability": capability},
            timeout=CATALOG_TIMEOUT_SECONDS,
            stream=True,
            allow_redirects=False,
        ) as response:
            if response.status_code in {401, 403}:
                raise CatalogAuthError
            if response.status_code != 200:
                logger.warning(f"OrcaRouter catalogue returned HTTP {response.status_code}")
                raise CatalogError
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=65536):
                total += len(chunk)
                if total > CATALOG_MAX_BYTES:
                    logger.warning("OrcaRouter catalogue exceeded the response size limit")
                    raise CatalogError
                chunks.append(chunk)
    except requests.RequestException:
        logger.warning("OrcaRouter catalogue request failed")
        raise CatalogError from None
    try:
        payload = json.loads(b"".join(chunks))
    except ValueError:
        raise CatalogError from None
    if not isinstance(payload, dict):
        raise CatalogError
    return payload


def _normalize_record(item: dict[str, Any]) -> dict[str, Any] | None:
    model_id = item.get("id")
    if not isinstance(model_id, str) or not model_id.strip():
        return None
    architecture = item.get("architecture")
    input_modalities: list[str] = []
    output_modalities: list[str] = []
    if isinstance(architecture, dict):
        if isinstance(architecture.get("input_modalities"), list):
            input_modalities = [str(value) for value in architecture["input_modalities"] if isinstance(value, str)]
        if isinstance(architecture.get("output_modalities"), list):
            output_modalities = [str(value) for value in architecture["output_modalities"] if isinstance(value, str)]
    context_window = item.get("context_length") or item.get("context_window")
    if not isinstance(context_window, int):
        top_provider = item.get("top_provider")
        context_window = top_provider.get("context_length") if isinstance(top_provider, dict) else None
        if not isinstance(context_window, int) or context_window <= 0:
            context_window = None
    fallback = _FALLBACK_BY_ID.get(model_id, {})
    reasoning_efforts = item.get("reasoning_efforts")
    if not isinstance(reasoning_efforts, list) or not reasoning_efforts:
        reasoning_efforts = fallback.get("reasoning_efforts", [])
    if not input_modalities:
        input_modalities = fallback.get("input_modalities", [])
    supported_endpoint_types = item.get("supported_endpoint_types")
    if not isinstance(supported_endpoint_types, list):
        supported_endpoint_types = fallback.get("supported_endpoint_types", [])
    return {
        "id": model_id,
        "name": item.get("name") if isinstance(item.get("name"), str) else model_id,
        "supported_endpoint_types": [str(value) for value in supported_endpoint_types if isinstance(value, str)],
        "input_modalities": input_modalities,
        "output_modalities": output_modalities,
        "context_window": context_window,
        "reasoning_efforts": [str(value) for value in reasoning_efforts if isinstance(value, str)],
    }


def _parse_models(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = payload.get("data", payload.get("models", []))
    if not isinstance(raw_items, list):
        raise CatalogError
    models: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_items[:CATALOG_MAX_ITEMS]:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_record(item)
        if normalized is None or normalized["id"] in seen:
            continue
        seen.add(normalized["id"])
        models.append(normalized)
    return models


def _fallback_models(api_format: str, capability: str, required_input_modalities: tuple[str, ...]) -> list[dict[str, Any]]:
    return [
        {
            **model,
            "output_modalities": ["text"],
            "context_window": model.get("context_window"),
        }
        for model in filter_catalog_models(
            [dict(model) for model in ORCAROUTER_FALLBACK_MODELS],
            capability,
            api_format=api_format,
            required_input_modalities=required_input_modalities,
        )
    ]


def orcarouter_catalog(
    *,
    api_format: str,
    base_url: str = "",
    api_key: str = "",
    required_input_modalities: tuple[str, ...] = (),
    refresh: bool = False,
) -> CatalogResult:
    """Return the model options for one OrcaRouter wire format.

    Raises ``CatalogAuthError`` for rejected credentials, ``CatalogRequestError``
    for an invalid base URL, and ``CatalogError`` when the catalogue cannot be
    reached or parsed. The caller renders the verified fallback catalogue on
    those failures and never sees upstream response text or the API key.
    """
    capability = SUPPORTED_API_FORMATS.get(api_format)
    if capability is None:
        raise CatalogRequestError
    resolved_base_url = _validate_base_url(base_url or ORCAROUTER_DEFAULT_BASE_URL)
    key = _cache_key(resolved_base_url, api_key, api_format, capability, required_input_modalities)
    if not refresh and (cached := _read_cached(key)) is not None:
        return CatalogResult(models=cached, source="live", cached=True)
    payload = _download(_catalog_url(resolved_base_url), api_key, capability)
    models = [
        model
        for model in filter_catalog_models(
            _parse_models(payload),
            capability,
            api_format=api_format,
            required_input_modalities=required_input_modalities,
        )
    ]
    if not models:
        raise CatalogError
    _write_cache(key, models)
    return CatalogResult(models=models, source="live")


def orcarouter_fallback(
    *,
    api_format: str,
    required_input_modalities: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    capability = SUPPORTED_API_FORMATS.get(api_format, "chat")
    return _fallback_models(api_format, capability, required_input_modalities)


def catalog_response(
    payload: dict[str, Any],
    *,
    saved_endpoint: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    """Build the JSON response for the admin catalogue endpoint."""
    provider = payload.get("provider", ORCAROUTER_PROVIDER_ID)
    api_format = payload.get("api_format", "chat_completions")
    if provider != ORCAROUTER_PROVIDER_ID:
        return {"error": "Model discovery is available for the OrcaRouter provider.", "code": "unsupported_provider"}, 400
    if api_format not in SUPPORTED_API_FORMATS:
        return {"error": "OrcaRouter supports Responses and Chat Completions.", "code": "unsupported_api_format"}, 400
    saved_endpoint = saved_endpoint or {}
    base_url = str(payload.get("base_url") or saved_endpoint.get("base_url") or ORCAROUTER_DEFAULT_BASE_URL)
    api_key = payload.get("api_key")
    if not isinstance(api_key, str) or not api_key.strip():
        api_key = str(saved_endpoint.get("api_key") or "")
    required = payload.get("required_input_modalities") or ()
    if not isinstance(required, (list, tuple)):
        required = ()
    required_modalities = tuple(str(value).casefold() for value in required if isinstance(value, str))
    default_model = str(saved_endpoint.get("default_model") or ORCAROUTER_DEFAULT_MODEL)
    try:
        result = orcarouter_catalog(
            api_format=api_format,
            base_url=base_url,
            api_key=api_key,
            required_input_modalities=required_modalities,
            refresh=bool(payload.get("refresh")),
        )
    except CatalogError as error:
        fallback = orcarouter_fallback(api_format=api_format, required_input_modalities=required_modalities)
        return {
            "error": error.public_message,
            "code": error.code,
            "source": "verified_fallback",
            "degraded": True,
            "cached": False,
            "api_format": api_format,
            "models": fallback,
            "count": len(fallback),
            "default_model": default_model,
        }, error.status
    return {
        "source": result.source,
        "degraded": False,
        "cached": result.cached,
        "api_format": api_format,
        "models": result.models,
        "count": len(result.models),
        "default_model": default_model,
        "base_url": _validate_base_url(base_url),
        "timeout": CATALOG_TIMEOUT_SECONDS,
    }, 200
