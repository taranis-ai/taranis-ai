import base64
import json
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from flask import render_template
from models.admin import OSINTSource
from models.types import COLLECTOR_TYPES

from frontend.cache import cache
from frontend.config import Config
from frontend.views.admin_views.dashboard_views import AdminDashboardView
from frontend.views.admin_views.report_type_views import ReportItemTypeView
from frontend.views.admin_views.source_views import SourceView
from frontend.views.base_view import BaseView


_VALID_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/iZk9HQAAAABJRU5ErkJggg=="
_VALID_PNG_BYTES = base64.b64decode(_VALID_PNG_BASE64)


VIEW_ITEMS = BaseView._registry.items()
VIEW_IDS = list(BaseView._registry.keys())
CRUD_ITEMS = [(name, cls) for name, cls in VIEW_ITEMS if not getattr(cls, "_read_only", False)]
CRUD_IDS = [name for name, _ in CRUD_ITEMS]
ADMIN_VIEWS = [(name, cls) for name, cls in VIEW_ITEMS if getattr(cls, "_is_admin", False)]
ADMIN_IDS = [name for name, _ in ADMIN_VIEWS]


@pytest.mark.parametrize("view_name,view_cls", ADMIN_VIEWS, ids=ADMIN_IDS)
class TestAdminViews:
    def test_admin_views(self, view_name, view_cls):
        assert view_cls._is_admin
        assert view_cls.pretty_name() == view_name

    def test_list_view_renders(self, view_name, view_cls, authenticated_client, mock_core_get_endpoints):
        """
        For each BaseView subclass:
          - GET its base route (list view) → 200
          - the unique name we injected in mock_data appears in the HTML
        """

        payload = mock_core_get_endpoints[view_name]
        target_url = view_cls.get_base_route()
        resp = authenticated_client.get(target_url)

        assert resp.status_code == 200, f"{view_name!r} list-view did not return 200 (got {resp.status_code})"

        html = resp.get_data(as_text=True)

        expected = payload.get("_expect_object", None)
        assert expected is not None, f"Expected: {expected} item in {view_name!r} not found in payload: {payload!r}"

        assert expected in html, f"Expected {expected!r} in the {view_name!r} HTML but did not find it.\nHTML snippet: {html[200:500]}…"


@pytest.mark.parametrize("view_name,view_cls", CRUD_ITEMS, ids=CRUD_IDS)
class TestCRUDViews:
    def test_create_form_renders(
        self, view_name, view_cls, form_data, form_formats_from_models, authenticated_client, mock_core_get_endpoints
    ):
        # GET the edit form for item_id
        item_id = "0"
        # from pdb import set_trace; set_trace()
        key = view_cls._get_object_key()
        url = view_cls.get_edit_route(**{key: item_id})
        resp = authenticated_client.get(url)
        assert resp.status_code == 200

        html = resp.get_data(as_text=True)
        print(f"FORMDATA FOR : {view_name}")
        print(form_formats_from_models[view_name])
        actual_keys = form_data(html).get_cleaned_keys()
        allowed = form_formats_from_models[view_name]["allowed"]
        required = form_formats_from_models[view_name]["required"]

        missing_required = required - actual_keys
        extra = actual_keys - allowed

        assert not missing_required, f"{view_name!r} missing required fields: {missing_required} from {actual_keys!r}"
        assert not extra, f"{view_name!r} has unexpected fields: {extra}"

    def test_update_form_renders(
        self, view_name, view_cls, form_data, mock_core_get_item_endpoints, form_formats_from_models, authenticated_client
    ):
        item_id = str(mock_core_get_item_endpoints[view_name]["id"])
        key = view_cls._get_object_key()
        url = view_cls.get_edit_route(**{key: item_id})
        resp = authenticated_client.get(url)
        assert resp.status_code == 200

        html = resp.get_data(as_text=True)
        actual_keys = form_data(html).get_cleaned_keys()
        allowed = form_formats_from_models[view_name]["allowed"]
        required = form_formats_from_models[view_name]["required"]

        missing_required = required - actual_keys
        extra = actual_keys - allowed

        assert not missing_required, f"{view_name!r} missing required fields: {missing_required} from {actual_keys!r}"
        assert not extra, f"{view_name!r} has unexpected fields: {extra}"

    # def test_create_form_submits(self, view_name, view_cls, mock_core_create_endpoints, authenticated_client):
    #     url = view_cls.get_base_route()
    #     resp = authenticated_client.post(url, data=mock_core_create_endpoints[view_name])
    #     assert resp.status_code == 200

    #     html = resp.get_data(as_text=True)
    #     assert "Successfully created" in html

    # def test_update_form_submits(self, view_name, view_cls, mock_core_update_endpoints, authenticated_client):
    #     # PUT to update existing item
    #     item_id = str(mock_core_update_endpoints[view_name]["items"][0]["id"])
    #     key = view_cls._get_object_key()
    #     url = view_cls.get_edit_route(**{key: item_id})
    #     resp = authenticated_client.put(url, data={})
    #     assert resp.status_code == 200

    #     html = resp.get_data(as_text=True)
    #     assert "Successfully updated" in html

    # def test_delete_form(self, view_name, view_cls, mock_core_delete_endpoints, authenticated_client):
    #     # DELETE existing item
    #     item_id = str(mock_core_delete_endpoints[view_name]["items"][0]["id"])
    #     url = view_cls.get_edit_route(item_id)
    #     resp = authenticated_client.delete(url)
    #     assert resp.status_code == 200

    #     html = resp.get_data(as_text=True)
    #     assert "Successfully deleted" in html


class TestSourceView:
    def test_import_post_view(self, authenticated_client):
        """
        Test that the import_post_view method correctly extracts the "sources" key
        from the uploaded JSON file.
        """
        # Create a dummy export file with a "sources" key
        dummy_export_data = {"version": 3, "sources": [{"name": "Test Source", "type": "rss", "url": "http://example.com/rss"}]}
        dummy_file_content = json.dumps(dummy_export_data).encode("utf-8")
        dummy_file = BytesIO(dummy_file_content)
        dummy_file.name = "test.json"

        # Mock the CoreApi().import_sources method
        with patch("frontend.views.admin_views.source_views.CoreApi") as mock_core_api:
            mock_api_instance = MagicMock()
            mock_core_api.return_value = mock_api_instance
            mock_api_instance.import_sources.return_value = MagicMock(ok=True)

            # Simulate the POST request
            resp = authenticated_client.post(
                SourceView.get_import_route(), data={"file": (dummy_file, "test.json")}, content_type="multipart/form-data"
            )

            assert resp.status_code == 302, f"Expected redirect response, got {resp.status_code}"
            assert resp.headers["Location"] == SourceView.get_base_route()

            mock_api_instance.import_sources.assert_called_once_with(dummy_export_data)

    def test_import_post_view_no_file(self, authenticated_client):
        """
        Test that the import_post_view method returns an error when no file is provided.
        """
        resp = authenticated_client.post(SourceView.get_import_route(), data={}, content_type="multipart/form-data")

        assert resp.status_code == 200, "Expected 200 OK response with error message in content"
        html = resp.get_data(as_text=True)
        assert "No file or organization provided" in html

    def test_import_post_view_api_failure(self, authenticated_client):
        """
        Test that the import_post_view method returns an error when the CoreApi call fails.
        """
        dummy_export_data = {"version": 3, "sources": [{"name": "Test Source", "type": "rss", "url": "http://example.com/rss"}]}
        dummy_file_content = json.dumps(dummy_export_data).encode("utf-8")
        dummy_file = BytesIO(dummy_file_content)
        dummy_file.name = "test.json"

        with patch("frontend.views.admin_views.source_views.CoreApi") as mock_core_api:
            mock_api_instance = MagicMock()
            mock_core_api.return_value = mock_api_instance
            mock_api_instance.import_sources.return_value = None

            resp = authenticated_client.post(
                SourceView.get_import_route(), data={"file": (dummy_file, "test.json")}, content_type="multipart/form-data"
            )

            assert resp.status_code == 200
            html = resp.get_data(as_text=True)
            assert "Failed to import sources" in html

    def test_process_form_data_accepts_valid_png_icon(self, app):
        with patch.object(SourceView, "store_form_data", return_value=({"stored": True}, None)) as mock_store:
            with app.test_request_context(
                SourceView.get_base_route(),
                method="POST",
                data={"icon": (BytesIO(_VALID_PNG_BYTES), "icon.png", "image/png")},
                content_type="multipart/form-data",
            ):
                response, error = SourceView.process_form_data(0)

        assert error is None
        assert response == {"stored": True}
        mock_store.assert_called_once()
        processed_data = mock_store.call_args.args[0]
        assert processed_data["icon"] == base64.b64encode(_VALID_PNG_BYTES).decode("utf-8")

    def test_process_form_data_rejects_oversized_icon(self, app):
        max_bytes = Config.OSINT_SOURCE_ICON_MAX_BYTES
        oversized_icon = b"\x00" * (max_bytes + 1)

        with patch.object(SourceView, "store_form_data") as mock_store:
            with app.test_request_context(
                SourceView.get_base_route(),
                method="POST",
                data={"icon": (BytesIO(oversized_icon), "icon.png", "image/png")},
                content_type="multipart/form-data",
            ):
                response, error = SourceView.process_form_data(0)

        assert response is None
        assert error == f"Icon file exceeds maximum size of {max_bytes} bytes."
        mock_store.assert_not_called()

    def test_process_form_data_returns_core_error_message(self, app):
        with patch.object(SourceView, "store_form_data", return_value=(None, {"error": "Icon payload is not a valid image file."})):
            with app.test_request_context(
                SourceView.get_base_route(),
                method="POST",
                data={"icon": (BytesIO(b"not-an-image"), "icon.png", "image/png")},
                content_type="multipart/form-data",
            ):
                response, error = SourceView.process_form_data(0)

        assert response is None
        assert error == "Icon payload is not a valid image file."

    def test_process_form_data_can_delete_icon_without_upload(self, app):
        with patch.object(SourceView, "store_form_data", return_value=({"stored": True}, None)) as mock_store:
            with app.test_request_context(
                SourceView.get_base_route(),
                method="POST",
                data={"delete_icon": "true"},
                content_type="multipart/form-data",
            ):
                response, error = SourceView.process_form_data(123)

        assert error is None
        assert response == {"stored": True}
        mock_store.assert_called_once()
        processed_data = mock_store.call_args.args[0]
        assert processed_data["icon"] == ""
        assert "delete_icon" not in processed_data


def test_report_item_type_submitted_form_model_uses_shared_normalization(app):
    with app.test_request_context(
        "/admin/report-item-types/0",
        method="POST",
        data={
            "title": "Incident Report",
            "description": "Shared normalization",
            "attribute_groups[][index]": "0",
            "attribute_groups[][title]": "Indicators",
            "attribute_groups[][attribute_group_items][][index]": "0",
            "attribute_groups[][attribute_group_items][][title]": "Domain",
            "csrf_token": "secret",
        },
    ):
        model = ReportItemTypeView._submitted_form_model()

    assert model is not None
    assert model.title == "Incident Report"
    assert len(model.attribute_groups or []) == 1
    assert model.attribute_groups[0].title == "Indicators"
    assert len(model.attribute_groups[0].attribute_group_items) == 1
    assert model.attribute_groups[0].attribute_group_items[0].title == "Domain"

    def test_process_form_data_delete_icon_wins_over_file_upload(self, app):
        max_bytes = Config.OSINT_SOURCE_ICON_MAX_BYTES
        oversized_icon = b"\x00" * (max_bytes + 1)

        with patch.object(SourceView, "store_form_data", return_value=({"stored": True}, None)) as mock_store:
            with app.test_request_context(
                SourceView.get_base_route(),
                method="POST",
                data={"delete_icon": "true", "icon": (BytesIO(oversized_icon), "icon.png", "image/png")},
                content_type="multipart/form-data",
            ):
                response, error = SourceView.process_form_data(123)

        assert error is None
        assert response == {"stored": True}
        mock_store.assert_called_once()
        processed_data = mock_store.call_args.args[0]
        assert processed_data["icon"] == ""

    def test_osint_source_form_shows_current_icon_and_delete_option(self, app):
        osint_source = OSINTSource.model_construct(
            id="source-with-icon",
            name="Test source",
            description="",
            rank=3,
            type=COLLECTOR_TYPES.RSS_COLLECTOR,
            parameters={},
            icon=_VALID_PNG_BASE64,
            enabled=True,
            status=None,
        )

        with app.test_request_context("/"):
            html = render_template(
                "osint_source/osint_source_form.html",
                model_name="osint_source",
                submit_text="Update OSINT Source",
                form_action="/frontend/admin/sources/source-with-icon",
                form_error={},
                osint_source=osint_source,
                icon_accept="image/png",
                collector_types=[],
                parameters=[],
                parameter_values={},
            )

        assert "Current icon" in html
        assert "An icon is currently uploaded." in html
        assert 'name="delete_icon"' in html
        assert 'data-testid="current-osint-icon"' in html
        assert 'data-testid="osint-source-rank"' in html
        assert 'value="3"' in html
        assert 'aria-label="3 stars"' in html
        assert "checked" in html

    def test_osint_source_form_disables_rank_for_manual_source(self, app):
        osint_source = OSINTSource.model_construct(
            id="manual",
            name="Manual",
            description="",
            rank=0,
            type=COLLECTOR_TYPES.MANUAL_COLLECTOR,
            parameters={},
            icon=None,
            enabled=True,
            status=None,
        )

        with app.test_request_context("/"):
            html = render_template(
                "osint_source/osint_source_form.html",
                model_name="osint_source",
                submit_text="Update OSINT Source",
                form_action='hx-put="/frontend/admin/sources/manual"',
                form_error={},
                osint_source=osint_source,
                icon_accept="image/png",
                collector_types=[],
                parameters=[],
                parameter_values={},
            )

        assert 'data-testid="osint-source-rank"' in html
        assert 'name="rank" value="0"' in html
        assert 'aria-label="Unrated"' in html
        assert html.count('name="rank"') == 7
        assert html.count("disabled") >= 6


def test_admin_dashboard_renders_health_card(authenticated_client, responses_mock, monkeypatch):
    for key in list(cache.cache._cache.keys()):
        if key.endswith("_dashboard"):
            cache.delete(key)

    monkeypatch.setattr(Config, "BUILD_DATE", datetime.fromisoformat("2025-01-16T08:45:00+00:00"))
    monkeypatch.setattr(Config, "GIT_INFO", {"tag": "1.3.5", "HEAD": "front456", "branch": "master"})

    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}{AdminDashboardView.model._core_endpoint}",
        json={
            "items": [
                {
                    "total_news_items": 10,
                    "total_story_items": 5,
                    "total_products": 2,
                    "report_items_completed": 3,
                    "report_items_in_progress": 1,
                    "latest_collected": "2025-01-14T21:16:42.699574+01:00",
                    "schedule_length": 4,
                    "conflict_count": 0,
                    "health_status": {
                        "healthy": False,
                        "services": {
                            "database": "up",
                            "broker": "down",
                            "workers": "down",
                        },
                    },
                    "worker_status": {},
                }
            ]
        },
        status=200,
        content_type="application/json",
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}{AdminDashboardView.model._core_endpoint}/build-info",
        json={
            "build_date": "2025-01-15T09:30:00+00:00",
            "tag": "1.3.4",
            "HEAD": "core123",
            "branch": "master",
        },
        status=200,
        content_type="application/json",
    )

    response = authenticated_client.get(AdminDashboardView.get_base_route())

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Release Info" in html
    assert "Core" in html
    assert "Frontend" in html
    assert "1.3.4" in html
    assert "core123" in html
    assert "1.3.5" in html
    assert "front456" in html
    assert "System Health" in html
    assert "Degraded" in html
    assert "database" in html
    assert "broker" in html
    assert "workers" in html


def test_admin_dashboard_renders_frontend_release_info_when_core_build_info_fails(authenticated_client, responses_mock, monkeypatch):
    for key in list(cache.cache._cache.keys()):
        if key.endswith("_dashboard"):
            cache.delete(key)

    monkeypatch.setattr(Config, "BUILD_DATE", datetime.fromisoformat("2025-01-16T08:45:00+00:00"))
    monkeypatch.setattr(Config, "GIT_INFO", {"tag": "1.3.5", "HEAD": "front456", "branch": "master"})

    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}{AdminDashboardView.model._core_endpoint}",
        json={
            "items": [
                {
                    "total_news_items": 10,
                    "total_story_items": 5,
                    "total_products": 2,
                    "report_items_completed": 3,
                    "report_items_in_progress": 1,
                    "latest_collected": "2025-01-14T21:16:42.699574+01:00",
                    "schedule_length": 4,
                    "conflict_count": 0,
                    "health_status": {
                        "healthy": True,
                        "services": {
                            "database": "up",
                            "broker": "up",
                            "workers": "up",
                        },
                    },
                    "worker_status": {},
                }
            ]
        },
        status=200,
        content_type="application/json",
    )
    responses_mock.get(
        f"{Config.TARANIS_CORE_URL}{AdminDashboardView.model._core_endpoint}/build-info",
        json={"message": "unavailable"},
        status=503,
        content_type="application/json",
    )

    response = authenticated_client.get(AdminDashboardView.get_base_route())

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Frontend" in html
    assert "1.3.5" in html
    assert "front456" in html
    assert "Unavailable" in html
