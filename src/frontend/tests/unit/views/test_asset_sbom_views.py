import json

import pytest
from lxml import html
from models.sbom import SbomComparison, SbomInventory, SbomSummary

from frontend.cache import add_user_to_cache
from frontend.config import Config


@pytest.mark.parametrize(
    ("target_id", "software_matching", "cve_matching"), [(None, False, True), ("asset-1", True, False), (None, False, False)]
)
def test_confirmation_preserves_matching_choices_after_error(
    authenticated_client, auth_user, responses_mock, target_id, software_matching, cve_matching
):
    user = auth_user.model_copy(deep=True)
    user.permissions.append("ASSETS_CREATE")
    add_user_to_cache(user.model_dump(mode="json"))
    preview = SbomInventory(
        id="preview-1",
        filename="host.cdx.json",
        sha256="new-hash",
        imported_at="2026-10-21T12:00:00",
        summary=SbomSummary(
            spec_version="1.6",
            document_version=1,
            software_records=0,
            excluded_files=0,
            component_count=0,
            components_with_cpes=0,
            invalid_cpe_count=0,
        ),
        components=[],
        page=1,
        pages=1,
        comparison=SbomComparison(
            asset_id=target_id,
            asset_name="Host",
            expected_sha256="old-hash",
            components_added=0,
            components_removed=0,
            findings_added=0,
            findings_removed=0,
            cves_added=0,
            cves_removed=0,
            clears_findings=False,
        )
        if target_id
        else None,
    )
    preview_url = f"{Config.TARANIS_CORE_URL}/assets/sbom-imports/{preview.id}"
    apply_url = f"{Config.TARANIS_CORE_URL}/assets/{target_id}/sbom" if target_id else preview_url
    method = "PUT" if target_id else "POST"
    responses_mock.get(preview_url, json=preview.model_dump(mode="json"))
    responses_mock.get(f"{Config.TARANIS_CORE_URL}/asset-groups", json={"items": [{"id": "default", "name": "Default"}]})
    responses_mock.add(method, apply_url, json={"error": "Review the confirmation."}, status=400)
    form = {"name": "Host", "asset_group_id": "default", "expected_sha256": "old-hash"}
    if software_matching:
        form["enable_software_matching"] = "on"
    if cve_matching:
        form["enable_cve_matching"] = "on"
    route = f"/assets/sbom-imports/{preview.id}"
    response = authenticated_client.post(route, query_string={"asset_id": target_id} if target_id else {}, data=form)
    assert response.status_code == 400
    submitted = json.loads(next(call.request.body for call in responses_mock.calls if call.request.method == method))
    assert submitted["enable_software_matching"] == software_matching
    assert submitted["enable_cve_matching"] == cve_matching
    tree = html.fromstring(response.text)
    assert bool(tree.xpath('//input[@name="enable_software_matching"]/@checked')) == software_matching
    assert bool(tree.xpath('//input[@name="enable_cve_matching"]/@checked')) == cve_matching
    responses_mock.replace(method, apply_url, json={"id": target_id or "created-1"}, status=200)
    retried = authenticated_client.post(route, query_string={"asset_id": target_id} if target_id else {}, data=form)
    assert retried.status_code == 303
    assert retried.location.endswith(f"/assets/{target_id or 'created-1'}/intelligence")
