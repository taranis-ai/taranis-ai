import json

from flask import url_for
from lxml import html

from frontend.config import Config


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
    response = authenticated_client.post(route, headers=headers, data={"action": "reprocess"})
    assert response.status_code == 202
    assert "HRAG indexing queued" in response.text
    submitted = next(call for call in responses_mock.calls if call.request.method == "POST")
    assert json.loads(submitted.request.body) == {"action": "backfill"}

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
        "3",
        "2",
        "1",
        "7",
    ]

    responses_mock.post(upstream, json={"error": "Queue unavailable"}, status=503)
    response = authenticated_client.post(route, headers=headers)
    assert response.status_code == 503 and "Could not start HRAG indexing" in response.text
    responses_mock.get(upstream, json={"enabled": False, "generations": []})
    response = authenticated_client.get(route, headers=headers)
    assert "HRAG is disabled" in response.text and "Start indexing" not in response.text
    responses_mock.get(upstream, status=503)
    assert "indexing status is unavailable" in authenticated_client.get(route, headers=headers).text
