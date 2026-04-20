from flask import url_for

from frontend.config import Config


def test_report_view_renders_access_denied_page_when_core_returns_403(app, authenticated_client_basic, responses_mock):
    report_id = "12676a74-0850-4eef-971b-a4efd9d526e6"
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/analyze/report-items/{report_id}",
        json={"error": f"User 2 is not allowed to read Report {report_id}"},
        status=403,
        content_type="application/json",
    )

    with app.test_request_context():
        response = authenticated_client_basic.get(url_for("analyze.report", report_id=report_id))

    assert response.status_code == 403
    html = response.get_data(as_text=True)
    assert "403 - Access denied" in html


def test_story_view_renders_access_denied_page_when_core_returns_403(app, authenticated_client_basic, responses_mock):
    story_id = "12676a74-0850-4eef-971b-a4efd9d526e6"
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/assess/stories/{story_id}",
        json={"error": f"User 2 is not allowed to read Story {story_id}"},
        status=403,
        content_type="application/json",
    )

    with app.test_request_context():
        response = authenticated_client_basic.get(url_for("assess.story", story_id=story_id))

    assert response.status_code == 403
    html = response.get_data(as_text=True)
    assert "403 - Access denied" in html
