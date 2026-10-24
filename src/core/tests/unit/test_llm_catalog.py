import json

import pytest
import requests

from core.service import llm_catalog
from core.service.llm_catalog import (
    CatalogAuthError,
    CatalogError,
    CatalogRequestError,
    catalog_response,
    orcarouter_catalog,
)


def _response(payload: dict, status: int = 200) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.headers["Content-Type"] = "application/json"
    response._content = json.dumps(payload).encode()
    response._content_consumed = True
    return response


CATALOG = {
    "data": [
        {
            "id": "orcarouter/auto",
            "name": "OrcaRouter Auto",
            "supported_endpoint_types": ["openai", "openai-response", "anthropic", "gemini"],
            "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            "context_length": 1000000,
        },
        {
            "id": "orca/orcacyber-ultra-1.0",
            "name": "OrcaCyber Ultra",
            "supported_endpoint_types": ["openai"],
            "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            "context_length": 1048576,
        },
        {
            "id": "vision/model",
            "supported_endpoint_types": ["openai"],
            "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
        },
        {
            "id": "image/generator",
            "supported_endpoint_types": ["image-generation"],
            "architecture": {"input_modalities": ["text"], "output_modalities": ["image"]},
        },
        {"id": "text/embedding", "supported_endpoint_types": ["embeddings"]},
        {"id": "text/no-modalities", "supported_endpoint_types": ["openai"]},
    ]
}


@pytest.fixture
def catalog_cache():
    llm_catalog.clear_cache()
    yield
    llm_catalog.clear_cache()


def test_catalog_filters_each_wire_format_and_required_modalities(catalog_cache, monkeypatch):
    monkeypatch.setattr(llm_catalog.requests, "get", lambda *args, **kwargs: _response(CATALOG))

    responses = orcarouter_catalog(api_format="responses", api_key="test-key")
    assert [model["id"] for model in responses.models] == ["orcarouter/auto"]

    chat = orcarouter_catalog(api_format="chat_completions", api_key="test-key")
    assert [model["id"] for model in chat.models] == [
        "orcarouter/auto",
        "orca/orcacyber-ultra-1.0",
        "vision/model",
        "text/no-modalities",
    ]

    multimodal = orcarouter_catalog(api_format="chat_completions", api_key="test-key", required_input_modalities=("image",))
    assert [model["id"] for model in multimodal.models] == ["vision/model"]


def test_catalog_uses_saved_key_server_side_and_caches(catalog_cache, monkeypatch):
    calls = []

    def get(*args, **kwargs):
        calls.append(kwargs)
        return _response(CATALOG)

    monkeypatch.setattr(llm_catalog.requests, "get", get)
    payload, status = catalog_response(
        {"api_format": "chat_completions"},
        saved_endpoint={"base_url": "https://api.orcarouter.ai/v1", "api_key": "saved-key"},
    )

    assert status == 200
    assert payload["source"] == "live"
    assert payload["degraded"] is False
    assert calls[0]["headers"]["Authorization"] == "Bearer saved-key"
    assert calls[0]["params"] == {"capability": "chat"}
    assert "saved-key" not in json.dumps(payload)

    catalog_response({"api_format": "chat_completions"}, saved_endpoint={"base_url": "https://api.orcarouter.ai/v1", "api_key": "saved-key"})
    assert len(calls) == 1

    cached_payload, _ = catalog_response(
        {"api_format": "chat_completions"}, saved_endpoint={"base_url": "https://api.orcarouter.ai/v1", "api_key": "saved-key"}
    )
    assert cached_payload["cached"] is True

    catalog_response(
        {"api_format": "chat_completions", "refresh": True},
        saved_endpoint={"base_url": "https://api.orcarouter.ai/v1", "api_key": "saved-key"},
    )
    assert len(calls) == 2


def test_catalog_auth_failure_is_curated_and_degrades_to_verified_fallback(catalog_cache, monkeypatch):
    monkeypatch.setattr(llm_catalog.requests, "get", lambda *args, **kwargs: _response({}, status=401))

    with pytest.raises(CatalogAuthError) as error:
        orcarouter_catalog(api_format="chat_completions", api_key="sk-orca-rejected")
    assert "sk-orca-rejected" not in str(error.value)

    payload, status = catalog_response(
        {"api_format": "chat_completions", "api_key": "sk-orca-rejected"},
        saved_endpoint={"base_url": "https://api.orcarouter.ai/v1"},
    )
    assert status == 401
    assert payload["code"] == "catalog_auth_failed"
    assert payload["degraded"] is True
    assert payload["source"] == "verified_fallback"
    assert "OrcaRouter rejected this API key" in payload["error"]
    assert "sk-orca-rejected" not in json.dumps(payload)
    assert any(model["id"] == "orcarouter/auto" for model in payload["models"])


def test_catalog_network_and_invalid_base_url_fail_closed(catalog_cache, monkeypatch):
    def unavailable(*args, **kwargs):
        raise requests.ConnectionError("upstream detail")

    monkeypatch.setattr(llm_catalog.requests, "get", unavailable)
    with pytest.raises(CatalogError):
        orcarouter_catalog(api_format="chat_completions", api_key="test-key")

    with pytest.raises(CatalogRequestError):
        orcarouter_catalog(api_format="chat_completions", base_url="http://provider.example/v1")

    with pytest.raises(CatalogRequestError):
        orcarouter_catalog(api_format="systemone", base_url="https://api.orcarouter.ai/v1")

    payload, status = catalog_response(
        {"api_format": "chat_completions", "base_url": "http://provider.example/v1"},
        saved_endpoint={"api_key": "test-key"},
    )
    assert status == 400
    assert payload["code"] == "catalog_invalid_request"
    assert "upstream detail" not in json.dumps(payload)
