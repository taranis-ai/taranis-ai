import pytest
import json
from unittest.mock import patch, MagicMock
from io import BytesIO


from frontend.views.base_view import BaseView
from frontend.views.admin_views.source_views import SourceView


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
    def test_create_form_renders(self, view_name, view_cls, form_data, form_formats_from_models, authenticated_client):
        # GET the edit form for item_id
        item_id = "0"
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

            assert resp.status_code == 200, f"Expected 200 OK response, got {resp.status_code}"

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
