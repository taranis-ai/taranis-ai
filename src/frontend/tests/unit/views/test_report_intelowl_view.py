from typing import Any

from flask import render_template, url_for
from models.report import ReportItem

from frontend.config import Config


CTI_PAYLOAD = {
    "item_type": "report",
    "item_id": "report-1",
    "iocs": [
        {
            "ioc_type": "cve",
            "value": "CVE-2024-1234",
            "news_item_ids": ["news-1"],
            "enrichment": {
                "ioc_type": "cve",
                "value": "CVE-2024-1234",
                "status": "reported_without_fails",
                "job_id": "1",
                "job_url": "https://intelowl.example/jobs/1",
                "analyzers": [{"name": "NIST_CVE_DB", "status": "success", "report": {"score": 9.8}}],
                "errors": [],
                "submitted_at": "2026-07-06T10:00:00",
                "completed_at": "2026-07-06T10:01:00",
                "updated_at": "2026-07-06T10:01:00",
            },
        }
    ],
}


def _mock_cti(responses_mock: Any, path: str, item_type: str, item_id: str) -> None:
    payload = CTI_PAYLOAD | {"item_type": item_type, "item_id": item_id}
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}{path}",
        json=payload,
        status=200,
        content_type="application/json",
    )


def test_report_cti_dialog_loads(authenticated_client_basic: Any, responses_mock: Any) -> None:
    _mock_cti(responses_mock, "/analyze/report-items/report-1/cti", "report", "report-1")

    response = authenticated_client_basic.get(url_for("analyze.report_cti", report_id="report-1"))

    assert response.status_code == 200
    assert "CTI information" in response.text
    assert "CVE-2024-1234" in response.text
    assert "reported_without_fails" in response.text
    assert "NIST_CVE_DB" in response.text


def test_story_cti_dialog_loads(authenticated_client_basic: Any, responses_mock: Any) -> None:
    _mock_cti(responses_mock, "/assess/stories/story-1/cti", "story", "story-1")

    response = authenticated_client_basic.get(url_for("assess.story_cti", story_id="story-1"))

    assert response.status_code == 200
    assert "CTI information" in response.text
    assert "CVE-2024-1234" in response.text


def test_news_item_cti_dialog_loads(authenticated_client_basic: Any, responses_mock: Any) -> None:
    _mock_cti(responses_mock, "/assess/news-items/news-1/cti", "news_item", "news-1")

    response = authenticated_client_basic.get(url_for("assess.news_item_cti", news_item_id="news-1"))

    assert response.status_code == 200
    assert "CTI information" in response.text
    assert "CVE-2024-1234" in response.text


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
    assert "intel_owl_bot" not in html
    assert "IntelOwl" not in html
