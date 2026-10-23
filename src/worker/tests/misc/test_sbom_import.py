import json
from pathlib import Path

from worker.config import Config
from worker.misc.sbom_import import sbom_import_task


FIXTURE = Path(__file__).resolve().parents[3] / "core/tests/test_data/sbom/software.cdx.json"


def test_worker_prepares_inventory_in_bounded_batches(requests_mock):
    document = json.loads(FIXTURE.read_bytes())
    document["components"].extend({"type": "library", "name": f"package-{i}"} for i in range(150))
    document["vulnerabilities"] = [{"id": "CVE-2026-12345", "affects": [{"ref": "openssl-a"}]}]
    endpoint = f"{Config.TARANIS_CORE_URL}/worker/sbom-uploads/upload-id"
    requests_mock.get(endpoint, content=json.dumps(document).encode())
    begin = requests_mock.post(endpoint + "/begin", json={"status": "PROCESSING"})
    components = requests_mock.post(endpoint + "/components", json={"status": "PROCESSING"})
    findings = requests_mock.post(endpoint + "/findings", json={"status": "PROCESSING"})
    requests_mock.post(endpoint + "/complete", json={"status": "READY", "import_id": "preview-id"})
    result = sbom_import_task("upload-id")
    assert result == {"status": "READY", "import_id": "preview-id"}
    assert begin.last_request.json()["component_count"] == 153
    assert begin.last_request.json()["excluded_files"] == 1
    assert [r.json()["offset"] for r in components.request_history] == [0, 100]
    assert [len(r.json()["items"]) for r in components.request_history] == [100, 53]
    assert findings.last_request.json()["items"][0]["component_references"] == ["openssl-a"]


def test_worker_reports_curated_invalid_sbom_error(requests_mock):
    import pytest

    endpoint = f"{Config.TARANIS_CORE_URL}/worker/sbom-uploads/invalid"
    requests_mock.get(endpoint, content=b"private malformed source")
    failure = requests_mock.post(endpoint + "/failure", json={"status": "FAILED"})
    with pytest.raises(RuntimeError, match="SBOM preparation failed"):
        sbom_import_task("invalid")
    message = failure.last_request.json()["public_message"]
    assert "CycloneDX" in message
    assert "private malformed source" not in message
