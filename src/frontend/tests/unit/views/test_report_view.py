from flask import url_for
from models.report import ReportItem, ReportTypes

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


def test_report_delete_actions_target_notification_bar_on_error(app):
    with app.test_request_context():
        delete_action = next(action for action in ReportItemView.get_report_actions() if action["label"] == "Delete")

    assert delete_action["hx_target_error"] == "#notification-bar"


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


def test_report_update_response_fetches_saved_report_when_core_response_only_contains_id(app, monkeypatch):
    saved_report_id = "8124ae6f-3c85-49b4-93a1-9f3dc6516310"
    saved_report = ReportItem.model_construct(id=saved_report_id, title="test title", report_item_type_id=4)

    def mock_get_object(_self, model, object_id):
        assert model is ReportItem
        assert object_id == saved_report_id
        return saved_report

    def mock_get_objects(_self, model, *args, **kwargs):
        assert model is ReportTypes
        return [ReportTypes.model_construct(id=4, title="CERT Report")]

    monkeypatch.setattr(
        "frontend.views.base_view.BaseView.get_object_by_id", classmethod(lambda cls, object_id: mock_get_object(None, cls.model, object_id))
    )
    monkeypatch.setattr("frontend.views.report_views.DataPersistenceLayer.get_objects", mock_get_objects)

    with app.test_request_context("/report/0?layout=split"):
        persisted_object_id, model_instance, response_message = ReportItemView.resolve_update_response(
            0, {"id": saved_report_id, "message": "Report item created"}
        )
        context = ReportItemView.get_update_context(
            0,
            model_instance=model_instance,
            response_message=response_message,
            form_action_object_id=persisted_object_id,
        )

    assert context["report"].id == saved_report_id
    assert context["report"].title == "test title"
    assert context["submit_text"] == "Update Report"
    assert "hx-put=" in context["form_action"]


def test_report_create_post_renders_saved_report_when_core_response_only_contains_id(
    app, authenticated_client_basic, monkeypatch, responses_mock
):
    saved_report_id = "8124ae6f-3c85-49b4-93a1-9f3dc6516310"
    saved_report = ReportItem.model_construct(id=saved_report_id, title="test title", report_item_type_id=4)

    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/analyze/report-items",
        json={"id": saved_report_id, "message": "Report item created"},
        status=200,
        content_type="application/json",
    )

    def mock_get_object(_self, model, object_id):
        assert model is ReportItem
        assert object_id == saved_report_id
        return saved_report

    def mock_get_objects(_self, model, *args, **kwargs):
        assert model is ReportTypes
        return [ReportTypes.model_construct(id=4, title="CERT Report")]

    monkeypatch.setattr(
        "frontend.views.base_view.BaseView.get_object_by_id", classmethod(lambda cls, object_id: mock_get_object(None, cls.model, object_id))
    )
    monkeypatch.setattr("frontend.views.report_views.DataPersistenceLayer.get_objects", mock_get_objects)

    with app.test_request_context():
        response = authenticated_client_basic.post(
            url_for("analyze.report", report_id="0"),
            data={"title": "test title", "report_item_type_id": "4", "layout": "split"},
            headers={"HX-Request": "true"},
        )

    assert response.status_code == 200
    assert response.headers["HX-Push-Url"].endswith(f"/report/{saved_report_id}")
    html = response.get_data(as_text=True)
    assert f"ID: {saved_report_id}" in html
    assert 'value="test title"' in html
    assert "New Product from Report" in html
