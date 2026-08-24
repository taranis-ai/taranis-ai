from typing import Any

from flask import url_for
from lxml import html

from frontend.config import Config
from frontend.views.asset_views import AssetView


def _mock_report_cti(responses_mock: Any, analyzer: dict[str, Any]) -> None:
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/analyze/report-items/report-1/cti",
        json={
            "item_type": "report",
            "item_id": "report-1",
            "iocs": [
                {
                    "ioc_type": "cve",
                    "value": "CVE-2026-11405",
                    "news_item_ids": ["news-1"],
                    "enrichment": {
                        "ioc_type": "cve",
                        "value": "CVE-2026-11405",
                        "status": "reported_without_fails",
                        "analyzers": [analyzer],
                        "errors": [],
                    },
                }
            ],
        },
        status=200,
    )


def test_report_cti_view_renders_enrichment(authenticated_client_basic: Any, responses_mock: Any) -> None:
    _mock_report_cti(
        responses_mock,
        {
            "name": "NVD_CVE",
            "status": "SUCCESS",
            "report": {
                "format": "NVD_CVE",
                "vulnerabilities": [{"cve": {"id": "CVE-2026-11405", "vulnStatus": "Analyzed"}}],
            },
        },
    )

    response = authenticated_client_basic.get(url_for("analyze.report_cti", report_id="report-1"))

    assert response.status_code == 200
    assert 'data-testid="cti-view"' in response.text
    assert "CVE-2026-11405" in response.text
    assert "NVD_CVE" in response.text

    back_button = html.fromstring(response.text).get_element_by_id("cti-view").xpath('.//*[@data-testid="cti-back-link"]')[0]
    assert back_button.tag == "button"
    assert back_button.get("type") == "button"
    assert back_button.get("onclick") == "window.history.back()"
    assert back_button.get("href") is None


def test_cti_view_skips_non_http_external_links(authenticated_client_basic: Any, responses_mock: Any) -> None:
    _mock_report_cti(
        responses_mock,
        {
            "name": "VirusTotal_v3_Get_Observable",
            "status": "SUCCESS",
            "report": {"data": {"id": "example.com", "attributes": {}}, "link": "javascript:alert(1)"},
        },
    )

    response = authenticated_client_basic.get(url_for("analyze.report_cti", report_id="report-1"))

    assert response.status_code == 200
    assert "javascript:alert" not in response.text
    assert "Open in VirusTotal" not in response.text


def test_asset_observable_form_data_is_normalized() -> None:
    assert AssetView._normalize_form_data(
        {
            "name": "Asset",
            "asset_observables": [
                {"ioc_type": " domain ", "value": " example.com "},
                {"ioc_type": "", "value": ""},
            ],
        }
    ) == {"name": "Asset", "asset_observables": [{"ioc_type": "domain", "value": "example.com"}]}
