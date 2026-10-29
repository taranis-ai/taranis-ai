import pytest
from lxml import html

from frontend.config import Config


@pytest.mark.parametrize("asset_id", [None, "host-1"])
def test_cve_pages_read_current_inventory_and_handle_upstream_failure(authenticated_client, responses_mock, asset_id):
    endpoint = f"/assets/{asset_id}/cves" if asset_id else "/assets/cves"
    api_url = f"{Config.TARANIS_CORE_URL}{endpoint}"
    payload = {"page": 1, "limit": 20, "total_count": 1}
    if asset_id:
        payload.update(asset_id=asset_id, asset_name="Host", items=[{"cve_id": "CVE-2026-12345", "manual": True}])
    else:
        payload.update(groups=[], tags=[], items=[{"id": "host-1", "name": "Host", "group_name": "Default", "tags": []}])
    responses_mock.get(api_url, json=payload)
    response = authenticated_client.get(endpoint)
    assert response.status_code == 200
    assert len(html.fromstring(response.text).xpath("//tbody/tr[@data-test-id]")) == 1
    responses_mock.replace("GET", api_url, json=payload | {"items": [], "total_count": 0})
    current = authenticated_client.get(endpoint, headers={"HX-Request": "true"})
    assert current.status_code == 200
    assert not html.fromstring(current.text).xpath("//tbody/tr[@data-test-id]")
    responses_mock.replace("GET", api_url, json={"error": "private upstream details"}, status=403)
    failed = authenticated_client.get(endpoint)
    assert failed.status_code == 403
    assert "private upstream details" not in failed.text
    assert html.fromstring(failed.text).xpath('//*[@role="alert"]')
