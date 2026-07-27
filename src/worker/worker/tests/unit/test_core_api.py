from worker.config import Config
from worker.core_api import CoreApi


def test_update_osint_source_icon_skips_empty_file(requests_mock):
    assert CoreApi().update_osint_source_icon("source-1", {"file": ("favicon.ico", b"")}) is None

    assert requests_mock.request_history == []


def test_update_osint_source_icon_sends_multipart_file(requests_mock):
    requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/osint-sources/source-1/icon", json={"message": "Icon uploaded"})

    result = CoreApi().update_osint_source_icon("source-1", {"file": ("favicon.ico", b"icon")})

    assert result == {"message": "Icon uploaded"}
    assert requests_mock.request_history[0].headers["Content-Type"].startswith("multipart/form-data")
