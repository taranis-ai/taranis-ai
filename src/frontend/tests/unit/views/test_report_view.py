from unittest.mock import patch

from flask import url_for
from models.admin import ReportItemAttribute
from models.report import ReportItem, ReportItemAttributeGroup, ReportTypes

from frontend.config import Config
from frontend.views.report_views import ReportItemView


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


def test_report_view_preserves_unsaved_attribute_values_on_layout_switch(app):
    report = ReportItem(
        id="report-1",
        title="persisted title",
        report_item_type_id=4,
        grouped_attributes=[
            ReportItemAttributeGroup(
                title="Narrative and Timing",
                attributes=[
                    ReportItemAttribute(id=1, title="Date", value="today", type="DATE"),
                    ReportItemAttribute(id=2, title="Timeframe", value="last week", type="TEXT"),
                ],
            )
        ],
    )

    with app.test_request_context(
        "/report/report-1",
        query_string={
            "layout": "split",
            "title": "edited title",
            "report_item_type_id": "4",
            "attributes[1]": "yesterday",
            "attributes[2]": "this week",
        },
    ):
        with patch("frontend.views.base_view.DataPersistenceLayer.get_object", return_value=report):
            with patch("frontend.views.report_views.DataPersistenceLayer.get_objects", return_value=[]):
                context = ReportItemView.get_item_context("report-1")

    rendered_report = context["report"]
    assert rendered_report.title == "edited title"
    assert rendered_report.report_item_type_id == 4
    assert rendered_report.grouped_attributes[0].attributes[0].value == "yesterday"
    assert rendered_report.grouped_attributes[0].attributes[1].value == "this week"


def test_create_report_view_preserves_unsaved_values_on_layout_switch(app):
    with app.test_request_context(
        "/report/0",
        query_string={
            "layout": "split",
            "title": "draft title",
            "report_item_type_id": "4",
        },
    ):
        with patch("frontend.views.report_views.DataPersistenceLayer.get_objects", return_value=[]):
            context = ReportItemView.get_create_context()

    rendered_report = context["report"]
    assert rendered_report.id == "0"
    assert rendered_report.title == "draft title"
    assert rendered_report.report_item_type_id == 4


def test_create_report_route_renders_submitted_values(authenticated_client):
    report_types = [ReportTypes(id=4, title="Daily Report")]

    with authenticated_client.application.app_context():
        target_url = url_for("analyze.report", report_id="0", layout="split", title="draft title", report_item_type_id="4")

    with patch("frontend.views.report_views.DataPersistenceLayer.get_objects", return_value=report_types):
        response = authenticated_client.get(target_url)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'value="draft title"' in html
    assert '<option value="4" selected>' in html
