import json

from flask import url_for
from lxml import html

from frontend.config import Config


def test_llm_assignments_filter_capabilities_and_preserve_unavailable_selection(authenticated_client, responses_mock):
    provider = {"base_url": "https://provider.example/v1", "enabled": True}
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/settings/settings",
        json={
            "items": [
                {
                    "settings": {
                        "llm_endpoints": {
                            "generative": {**provider, "name": "Generative provider", "api_formats": {"responses": {}}},
                            "embedding": {**provider, "name": "Embedding provider", "api_formats": {"embeddings": {}}},
                            "decisions": {**provider, "name": "Decisions provider", "api_formats": {"systemone": {}}},
                            "disabled": {**provider, "name": "Disabled provider", "enabled": False, "api_formats": {"responses": {}}},
                            "batch": {
                                **provider,
                                "name": "Batch provider",
                                "processing_mode": "openrouter_batch",
                                "api_formats": {"responses": {}},
                            },
                        },
                        "llm_default_endpoint": "generative",
                        "llm_embedding_endpoint": "generative",
                    }
                }
            ],
            "total_count": 1,
        },
    )
    response = authenticated_client.get(url_for("admin_settings.settings"))
    assert response.status_code == 200
    selects = {
        select.get("name"): {option.get("value"): option.text for option in select.xpath("./option")}
        for select in html.fromstring(response.text).xpath('.//form[@data-test-id="llm-assignments"]//select')
    }
    assert selects["settings[llm_chat_endpoint]"] == {"": "Use default", "generative": "Generative provider"}
    assert selects["settings[llm_embedding_endpoint]"] == {
        "": "Use default",
        "embedding": "Embedding provider",
        "generative": "Generative provider (unavailable)",
    }
    assert selects["settings[llm_extraction_verification_endpoint]"] == {"": "Use default", "decisions": "Decisions provider"}
    assert selects["settings[llm_sentiment_endpoint]"] == {"": "Use default", "decisions": "Decisions provider"}
    assert selects["settings[llm_summarization_endpoint]"] == {
        "": "Use default",
        "generative": "Generative provider",
        "batch": "Batch provider",
    }


def test_hrag_indexing_start_refresh_and_failures(authenticated_client, responses_mock):
    route = url_for("admin_settings.hrag_indexing")
    upstream = f"{Config.TARANIS_CORE_URL}/settings/hrag"
    headers = {"HX-Request": "true"}
    responses_mock.get(
        upstream, json={"enabled": True, "generations": [], "configuration_errors": ["Configure HRAG relationship verification."]}
    )
    response = authenticated_client.get(route, headers=headers)
    assert response.status_code == 200
    assert "No indexing generations yet" in response.text
    assert "Start indexing" in response.text
    assert "Configure HRAG relationship verification." in response.text
    form = html.fromstring(response.text).xpath(".//form")[0]
    assert form.get("action") == route and form.get("hx-target") == "#settings-hrag-index"

    responses_mock.post(upstream, json={"message": "HRAG reconciliation queued"}, status=202)
    response = authenticated_client.post(route, headers=headers, data={"action": "backfill"})
    assert response.status_code == 202
    assert "HRAG indexing queued" in response.text
    submitted = next(call for call in responses_mock.calls if call.request.method == "POST")
    assert json.loads(submitted.request.body) == {"action": "backfill", "generation_id": ""}

    responses_mock.get(
        upstream,
        json={
            "enabled": True,
            "generations": [
                {
                    "id": "generation",
                    "pipeline": "embedding",
                    "active": True,
                    "model": "embedding-model",
                    "scanned": True,
                    "counts": {"ready": 7, "running": 1, "queued": 2, "pending": 3},
                }
            ],
        },
    )
    response = authenticated_client.get(route, headers=headers)
    table = html.fromstring(response.text).xpath(".//tbody/tr")[0]
    assert [cell.text_content().strip() for cell in table.xpath("./th | ./td")] == [
        "Embeddings",
        "embedding-model",
        "generation (Active)",
        "—",
        "",
        "3",
        "2",
        "1",
        "7",
    ]

    responses_mock.post(upstream, json={"message": "HRAG generation activated"})
    response = authenticated_client.post(route, headers=headers, data={"action": "activate", "generation_id": "replacement"})
    assert response.status_code == 200 and "HRAG generation activated" in response.text
    submitted = next(call for call in reversed(responses_mock.calls) if call.request.method == "POST")
    assert json.loads(submitted.request.body) == {"action": "activate", "generation_id": "replacement"}
    response = authenticated_client.post(route, headers=headers, data={"action": "activate"})
    assert response.status_code == 400

    responses_mock.post(upstream, json={"error": "Queue unavailable"}, status=503)
    response = authenticated_client.post(route, headers=headers)
    assert response.status_code == 503 and "Could not start HRAG indexing" in response.text
    responses_mock.get(upstream, json={"enabled": False, "generations": []})
    response = authenticated_client.get(route, headers=headers)
    assert "HRAG is disabled" in response.text and "Start indexing" not in response.text
    responses_mock.get(upstream, status=503)
    assert "indexing status is unavailable" in authenticated_client.get(route, headers=headers).text
