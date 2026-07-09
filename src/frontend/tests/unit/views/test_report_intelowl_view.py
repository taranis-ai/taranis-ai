from typing import Any

from flask import render_template, render_template_string, url_for
from models.assess import NewsItem, Story
from models.asset import Asset, AssetObservable
from models.report import ReportItem

from frontend.cache_models import CacheObject
from frontend.config import Config
from frontend.views.asset_views import AssetView


NVD_ANALYZER = {
    "name": "NVD_CVE",
    "status": "SUCCESS",
    "report": {
        "format": "NVD_CVE",
        "vulnerabilities": [
            {
                "cve": {
                    "id": "CVE-2026-11405",
                    "vulnStatus": "Deferred",
                    "metrics": {
                        "cvssMetricV31": [
                            {
                                "cvssData": {
                                    "baseScore": 9.8,
                                    "baseSeverity": "CRITICAL",
                                    "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                                    "attackVector": "NETWORK",
                                    "privilegesRequired": "NONE",
                                    "userInteraction": "NONE",
                                }
                            }
                        ],
                        "ssvcV203": [{"ssvcData": {"options": [{"exploitation": "none"}, {"automatable": "yes"}]}}],
                    },
                    "descriptions": [{"lang": "en", "value": "Hidden backdoor authentication mechanism."}],
                    "affected": [
                        {
                            "affectedData": [
                                {
                                    "vendor": "Tenda",
                                    "product": "firmware",
                                    "versions": [{"version": "US_AC6V2.0RTL_V15.03.06.51_multi_T"}],
                                }
                            ]
                        }
                    ],
                    "references": [{"url": "https://kb.cert.org/vuls/id/213560"}],
                }
            }
        ],
    },
    "errors": [],
}

VIRUSTOTAL_ANALYZER = {
    "name": "VirusTotal_v3_Get_Observable",
    "status": "SUCCESS",
    "report": {
        "data": {
            "id": "example.com",
            "type": "domain",
            "links": {"self": "https://www.virustotal.com/api/v3/domains/example.com"},
            "attributes": {
                "title": "Example domain",
                "reputation": 0,
                "last_analysis_stats": {"malicious": 0, "suspicious": 1, "harmless": 56, "undetected": 35, "timeout": 0},
                "last_analysis_results": {
                    "ExampleEngine": {"category": "suspicious", "result": "phishing"},
                    "CleanEngine": {"category": "harmless", "result": "clean"},
                },
            },
        },
        "link": "https://www.virustotal.com/gui/domain/example.com",
    },
    "errors": [],
}

URLHAUS_ANALYZER = {"name": "URLhaus", "status": "SUCCESS", "report": {"query_status": "no_results"}, "errors": []}


def _cti_payload(item_type: str, item_id: str, analyzers: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "item_type": item_type,
        "item_id": item_id,
        "iocs": [
            {
                "ioc_type": "cve",
                "value": "CVE-2026-11405",
                "news_item_ids": ["news-1"],
                "enrichment": {
                    "ioc_type": "cve",
                    "value": "CVE-2026-11405",
                    "status": "reported_without_fails",
                    "analyzers": analyzers or [NVD_ANALYZER],
                    "errors": [],
                    "submitted_at": "2026-07-06T10:00:00",
                    "completed_at": "2026-07-06T10:01:00",
                    "updated_at": "2026-07-06T10:01:00",
                },
            }
        ],
    }


def _mock_cti(responses_mock: Any, path: str, item_type: str, item_id: str, analyzers: list[dict[str, Any]] | None = None) -> None:
    payload = _cti_payload(item_type, item_id, analyzers)
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}{path}",
        json=payload,
        status=200,
        content_type="application/json",
    )


def test_report_cti_view_loads(authenticated_client_basic: Any, responses_mock: Any) -> None:
    _mock_cti(responses_mock, "/analyze/report-items/report-1/cti", "report", "report-1")

    response = authenticated_client_basic.get(url_for("analyze.report_cti", report_id="report-1"))

    assert response.status_code == 200
    assert 'data-testid="cti-view"' in response.text
    assert "<dialog" not in response.text
    assert "CTI information" in response.text
    assert "CVE-2026-11405" in response.text
    assert "reported_without_fails" in response.text
    assert "NVD_CVE" in response.text
    assert "CRITICAL" in response.text
    assert "Hidden backdoor authentication mechanism." in response.text
    assert "Tenda" in response.text


def test_story_cti_view_loads(authenticated_client_basic: Any, responses_mock: Any) -> None:
    _mock_cti(responses_mock, "/assess/stories/story-1/cti", "story", "story-1")

    response = authenticated_client_basic.get(url_for("assess.story_cti", story_id="story-1"))

    assert response.status_code == 200
    assert "CTI information" in response.text
    assert "CVE-2026-11405" in response.text


def test_news_item_cti_view_loads(authenticated_client_basic: Any, responses_mock: Any) -> None:
    _mock_cti(responses_mock, "/assess/news-items/news-1/cti", "news_item", "news-1")

    response = authenticated_client_basic.get(url_for("assess.news_item_cti", news_item_id="news-1"))

    assert response.status_code == 200
    assert "CTI information" in response.text
    assert "CVE-2026-11405" in response.text


def test_asset_cti_view_loads(authenticated_client_basic: Any, responses_mock: Any) -> None:
    _mock_cti(responses_mock, "/assets/asset-1/cti", "asset", "asset-1")

    response = authenticated_client_basic.get(url_for("assets.asset_cti", asset_id="asset-1"))

    assert response.status_code == 200
    assert "CTI information" in response.text
    assert "CVE-2026-11405" in response.text


def test_assets_cti_view_loads(authenticated_client_basic: Any, responses_mock: Any) -> None:
    _mock_cti(responses_mock, "/assets/cti", "asset", "all")

    response = authenticated_client_basic.get(url_for("assets.assets_cti"))

    assert response.status_code == 200
    assert "CTI information" in response.text
    assert "CVE-2026-11405" in response.text


def test_cti_view_renders_virustotal_summary(authenticated_client_basic: Any, responses_mock: Any) -> None:
    _mock_cti(responses_mock, "/analyze/report-items/report-1/cti", "report", "report-1", [VIRUSTOTAL_ANALYZER])

    response = authenticated_client_basic.get(url_for("analyze.report_cti", report_id="report-1"))

    assert response.status_code == 200
    assert "VirusTotal_v3_Get_Observable" in response.text
    assert "Example domain" in response.text
    assert "Suspicious" in response.text
    assert "Open in VirusTotal" in response.text
    assert "ExampleEngine" in response.text


def test_cti_view_skips_non_http_external_links(authenticated_client_basic: Any, responses_mock: Any) -> None:
    analyzer = {
        "name": "VirusTotal_v3_Get_Observable",
        "status": "SUCCESS",
        "report": {"data": {"id": "example.com", "type": "domain", "attributes": {}}, "link": "javascript:alert(1)"},
        "errors": [],
    }
    _mock_cti(responses_mock, "/analyze/report-items/report-1/cti", "report", "report-1", [analyzer])

    response = authenticated_client_basic.get(url_for("analyze.report_cti", report_id="report-1"))

    assert response.status_code == 200
    assert "javascript:alert" not in response.text
    assert "Open in VirusTotal" not in response.text


def test_cti_view_renders_urlhaus_no_result(authenticated_client_basic: Any, responses_mock: Any) -> None:
    _mock_cti(responses_mock, "/analyze/report-items/report-1/cti", "report", "report-1", [URLHAUS_ANALYZER])

    response = authenticated_client_basic.get(url_for("analyze.report_cti", report_id="report-1"))

    assert response.status_code == 200
    assert "URLhaus returned no result for this observable." in response.text


def test_asset_template_shows_cti_button(app: Any) -> None:
    asset = Asset.model_construct(id="asset-1", name="Asset", asset_observables=[AssetObservable(ioc_type="domain", value="example.com")])

    with app.test_request_context("/assets/asset-1"):
        cti_url = url_for("assets.asset_cti", asset_id="asset-1")
        html = render_template(
            "assets/asset.html",
            asset=asset,
            asset_observables=[observable.model_dump(mode="json") for observable in asset.asset_observables],
            asset_observable_types=AssetView.observable_types,
            submit_text="Update asset",
            form_action="",
        )

    assert 'data-testid="asset-cti-button"' in html
    assert f'href="{cti_url}"' in html
    assert 'name="asset_observables[][ioc_type]"' in html
    assert 'name="asset_observables[][value]"' in html
    assert '"value": "example.com"' in html


def test_assets_table_shows_cti_button(app: Any) -> None:
    with app.test_request_context("/assets"):
        cti_url = url_for("assets.assets_cti")
        html = render_template(
            "assets/assets_table.html",
            assets=CacheObject([Asset.model_construct(id="asset-1", name="Asset", description="")]),
            model_plural_name="assets",
            model_name="asset",
            name="Assets",
            columns=AssetView.get_columns(),
            actions=[],
            routes={"base_route": "/assets", "edit_route": "/assets/"},
        )

    assert 'data-testid="assets-cti-button"' in html
    assert f'href="{cti_url}"' in html


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


def test_report_template_shows_cti_button_not_intelowl_run(app: Any) -> None:
    report = ReportItem.model_construct(
        id="report-1",
        title="Report",
        completed=False,
        report_item_type_id="report-type-1",
        grouped_attributes=[],
        stories=[],
        revision_count=0,
    )

    with app.test_request_context("/report/report-1"):
        cti_url = url_for("analyze.report_cti", report_id="report-1")
        html = render_template(
            "analyze/report.html",
            report=report,
            report_types=[],
            existing_products=[],
            submit_text="Edit report",
            form_action="/report/report-1",
            layout="split",
        )

    assert 'data-testid="report-cti-button"' in html
    assert f'href="{cti_url}"' in html
    assert "intel_owl_bot" not in html
    assert "IntelOwl" not in html


def test_story_cti_action_is_route_link(app: Any) -> None:
    story = Story.model_construct(id="story-1", read=False, important=False, revision_count=0)

    with app.test_request_context("/assess"):
        cti_url = url_for("assess.story_cti", story_id="story-1")
        html = render_template_string('{% from "assess/story_actions.html" import story_actions %}{{ story_actions(story) }}', story=story)

    assert 'data-testid="story-cti"' in html
    assert f'href="{cti_url}"' in html


def test_news_item_cti_action_is_route_link(app: Any) -> None:
    news_item = NewsItem.model_construct(id="news-1", story_id="story-1", title="News", tags=[])
    story = Story.model_construct(id="story-1", news_items=[news_item])

    with app.test_request_context("/assess/story/story-1"):
        cti_url = url_for("assess.news_item_cti", news_item_id="news-1")
        html = render_template_string(
            '{% from "assess/news_item_card.html" import news_item_card %}{{ news_item_card(news_item, story) }}',
            news_item=news_item,
            story=story,
        )

    assert 'data-testid="newsitem-cti-news-1"' in html
    assert f'href="{cti_url}"' in html
