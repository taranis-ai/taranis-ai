import pytest
from uuid import uuid4

from tests.functional.helpers import BaseTest


class TestAnalyzeApi(BaseTest):
    base_uri = "/api/analyze"

    def test_create_Report(self, client, auth_header, cleanup_report_item):
        """
        POST to /api/analyze/report-items endpoint to create a report.
        It expects a valid data and a valid status-code
        """
        response = self.assert_post_ok(client, "report-items", auth_header=auth_header, json_data=cleanup_report_item)
        assert response.get_json()["report"]["title"] == cleanup_report_item["title"]

    def test_get_Reports(self, client, auth_header, cleanup_report_item):
        """
        GET /api/analyze/report-items endpoint.
        It expects a valid data and a valid status-code
        """
        response = self.assert_get_ok(client, "report-items", auth_header)
        assert response.get_json()["total_count"] == 1
        items = response.get_json()["items"]
        assert len(items) == 1
        assert items[0]["title"] == cleanup_report_item["title"]

    def test_update_report(self, client, auth_header, cleanup_report_item):
        """
        PUT to /api/analyze/report-items/<report_id> endpoint to update an existing report
        It expects the response to reflect the updated report information
        """
        updated_data = {"title": "Updated Report Title"}
        report_id = cleanup_report_item["id"]
        url = f"report-items/{report_id}"
        response = self.assert_put_ok(client, url, json_data=updated_data, auth_header=auth_header)
        assert response.json["message"] == "Report item updated"
        assert response.json["report"]["title"] == "Updated Report Title"

    def test_clone_report(self, client, auth_header, cleanup_report_item):
        """
        POST to /api/analyze/report-items/<report_id>/clone endpoint to clone an existing report.
        It expects the response to include the cloned report's details
        """
        from core.model.report_item import ReportItem

        report_id = cleanup_report_item["id"]

        response = self.assert_post_ok(client, f"report-items/{report_id}/clone", {}, auth_header=auth_header)
        assert "id" in response.get_json() and response.get_json()["id"] != report_id, "Cloned report must have a different ID."
        cloned_report = ReportItem.get(response.get_json()["id"])
        assert cloned_report is not None
        assert cloned_report.user_id is not None

    def test_get_report_stories(self, client, auth_header, cleanup_report_item):
        """
        GET /api/analyze/report-items/<report_id>/stories to retrieve stories associated with a report.
        It expects a list of stories in the response
        """
        report_id = cleanup_report_item["id"]

        response = self.assert_get_ok(client, f"report-items/{report_id}/stories", auth_header=auth_header)
        assert response.get_json()["report"]["story_ids"] == [], "The response should be a list of stories."

    def test_update_report_stories(self, client, auth_header, cleanup_report_item, stories):
        """
        PUT to /api/analyze/report-items/<report_id>/stories endpoint to update stories within a report.
        It expects the updated stories to be reflected in the response
        """
        report_id = cleanup_report_item["id"]

        response = self.assert_put_ok(client, f"report-items/{report_id}/stories", json_data=stories, auth_header=auth_header)
        print(response.get_json())
        response_data = response.get_json()

        assert "Successfully updated Report Item" in response_data.get("message"), "The update operation should return a success message."

    def test_delete_report(self, client, auth_header, cleanup_report_item):
        """
        DELETE to /api/analyze/report-items/<report_id> endpoint to remove a report.
        It expects a successful deletion indicated by a 204 No Content status code
        """
        report_id = cleanup_report_item["id"]
        response = self.assert_delete_ok(client, f"report-items/{report_id}", auth_header=auth_header)
        assert "message" in response.text
        assert response.json["message"] == "Successfully deleted report 'Updated Report Title'"

    def test_get_report_item_passes_current_user_for_acl_check(self, client, auth_header, monkeypatch):
        captured_args: dict[str, object] = {}

        def fake_get_for_api(report_item_id: str, user=None):
            captured_args["report_item_id"] = report_item_id
            captured_args["user"] = user
            return {"id": report_item_id}, 200

        monkeypatch.setattr("core.api.analyze.report_item.ReportItem.get_for_api", fake_get_for_api)

        response = client.get("/api/analyze/report-items/report-1", headers=auth_header)
        assert response.status_code == 200
        assert captured_args["report_item_id"] == "report-1"
        assert captured_args["user"] is not None

    @pytest.mark.parametrize(
        "uri",
        [
            "report-items/report-1/revisions",
            "report-items/report-1/revisions/1",
        ],
    )
    def test_report_revision_endpoints_enforce_read_access(self, client, auth_header, monkeypatch, uri):
        def fake_get_for_api(_report_item_id: str, _user=None):
            return {"error": "forbidden"}, 403

        monkeypatch.setattr("core.api.analyze.report_item.ReportItem.get_for_api", fake_get_for_api)

        response = client.get(self.concat_url(uri), headers=auth_header)
        assert response.status_code == 403
        assert response.get_json() == {"error": "forbidden"}

    def test_hidden_report_type_cannot_be_forged_into_report_creation(self, app, client, auth_header_user_permissions):
        from core.managers.db_manager import db
        from core.model.report_item import ReportItem
        from core.model.report_item_type import ReportItemType
        from core.model.role import Role
        from core.model.role_based_access import ItemType, RoleBasedAccess

        acl_id = None
        created_report_id = f"forged-report-{uuid4()}"

        visible_before_acl = client.get(self.concat_url("report-types"), headers=auth_header_user_permissions)
        assert visible_before_acl.status_code == 200
        visible_type_ids = [item["id"] for item in visible_before_acl.get_json()["items"]]
        assert visible_type_ids, "Expected at least one report type visible to the non-admin test user"

        with app.app_context():
            admin_role = Role.filter_by_name("Admin")
            assert admin_role is not None
            protected_report_type = ReportItemType.get(visible_type_ids[0])
            assert protected_report_type is not None
            acl = RoleBasedAccess(
                name=f"report-type-acl-{uuid4()}",
                description="Restrict report type to admin role for regression test",
                item_type=ItemType.REPORT_ITEM_TYPE,
                item_id=str(protected_report_type.id),
                roles=[admin_role.id],
                read_only=False,
                enabled=True,
            )
            db.session.add(acl)
            db.session.commit()
            acl_id = acl.id
            protected_report_type_id = protected_report_type.id

        try:
            list_response = client.get(self.concat_url("report-types"), headers=auth_header_user_permissions)
            assert list_response.status_code == 200
            assert protected_report_type_id not in {item["id"] for item in list_response.get_json()["items"]}

            create_response = client.post(
                self.concat_url("report-items"),
                json={
                    "id": created_report_id,
                    "title": "Forged report",
                    "report_item_type_id": protected_report_type_id,
                    "stories": [],
                },
                headers=auth_header_user_permissions,
            )
            assert create_response.status_code == 403
            assert "not allowed to create Report" in create_response.get_json()["error"]
        finally:
            with app.app_context():
                if ReportItem.get(created_report_id):
                    ReportItem.delete(created_report_id)
                if acl_id and RoleBasedAccess.get(acl_id):
                    RoleBasedAccess.delete(acl_id)
