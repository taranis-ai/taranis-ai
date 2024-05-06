from tests.functional.helpers import BaseTest


class TestAnalyzeApi(BaseTest):
    base_uri = "/api/analyze"

    def test_create_Report(self, client, auth_header, cleanup_report_item):
        """
        POST to /api/analyze/report-items endpoint to create a report.
        It expects a valid data and a valid status-code
        """
        response = self.assert_post_ok(client, "report-items", auth_header=auth_header, json_data=cleanup_report_item)
        assert response.get_json()["title"] == cleanup_report_item["title"]

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
        assert response.json["message"] == "Successfully updated Report Item"
        response = self.assert_get_ok(client, url, auth_header)
        assert response.json["title"] == "Updated Report Title"

    def test_clone_report(self, client, auth_header, cleanup_report_item):
        """
        POST to /api/analyze/report-items/<report_id>/clone endpoint to clone an existing report.
        It expects the response to include the cloned report's details
        """
        report_id = cleanup_report_item["id"]

        response = self.assert_post_ok(client, f"report-items/{report_id}/clone", {}, auth_header=auth_header)
        assert "id" in response.get_json() and response.get_json()["id"] != report_id, "Cloned report must have a different ID."

    def test_get_report_stories(self, client, auth_header, cleanup_report_item):
        """
        GET /api/analyze/report-items/<report_id>/stories to retrieve stories associated with a report.
        It expects a list of stories in the response
        """
        report_id = cleanup_report_item["id"]

        response = self.assert_get_ok(client, f"report-items/{report_id}/stories", auth_header=auth_header)
        assert isinstance(response.get_json(), list), "The response should be a list of stories."

    def test_update_report_stories(self, client, auth_header, cleanup_report_item, stories):
        """
        PUT to /api/analyze/report-items/<report_id>/stories endpoint to update stories within a report.
        It expects the updated stories to be reflected in the response
        """
        report_id = cleanup_report_item["id"]

        response = self.assert_put_ok(client, f"report-items/{report_id}/stories", json_data=stories, auth_header=auth_header)
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
        assert response.json["message"] == "Report successfully deleted"
