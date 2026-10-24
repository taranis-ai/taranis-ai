import json
import os

import pytest

from core.service.llm_catalog import catalog_response


pytestmark = pytest.mark.skipif(
    not os.environ.get("ORCAROUTER_API_KEY"),
    reason="Live OrcaRouter credentials are not configured",
)


def test_live_orcarouter_catalog_returns_workspace_models():
    payload, status = catalog_response(
        {
            "provider": "orcarouter",
            "api_format": "chat_completions",
            "api_key": os.environ["ORCAROUTER_API_KEY"],
            "refresh": True,
        }
    )

    assert status == 200
    assert payload["source"] == "live"
    assert payload["degraded"] is False
    assert payload["count"] >= 3
    ids = {model["id"] for model in payload["models"]}
    assert {"orcarouter/auto", "orca/orcacyber-ultra-1.0", "orca/orcacyber-zero-1.5"} <= ids
    assert os.environ["ORCAROUTER_API_KEY"] not in json.dumps(payload)


def test_live_responses_catalog_only_returns_response_capable_models():
    payload, status = catalog_response(
        {
            "provider": "orcarouter",
            "api_format": "responses",
            "api_key": os.environ["ORCAROUTER_API_KEY"],
            "refresh": True,
        }
    )

    assert status == 200
    assert payload["models"]
    assert any(model["id"] == "orcarouter/auto" for model in payload["models"])
    assert all("openai-response" in model["supported_endpoint_types"] for model in payload["models"])


def test_live_orcarouter_chat_completion_through_core_chat_client():
    from core.model.settings import Settings as PersistentSettings
    from core.service.chat import ChatClient

    values = PersistentSettings.with_defaults(
        {
            "llm_endpoints": {
                "orca": {
                    "name": "OrcaRouter live",
                    "provider": "orcarouter",
                    "base_url": "https://api.orcarouter.ai/v1",
                    "enabled": True,
                    "api_key": os.environ["ORCAROUTER_API_KEY"],
                    "api_formats": {"chat_completions": {"model": "deepseek/deepseek-v4.1-flash"}},
                }
            },
            "llm_default_endpoint": "orca",
            "llm_chat_endpoint": "orca",
        }
    )
    deltas: list[str] = []
    result = ChatClient(settings=values).create_response([{"role": "user", "content": "Reply with the single word OK."}], deltas.append)

    assert "OK" in json.dumps(result).upper()
