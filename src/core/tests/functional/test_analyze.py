from tests.functional.helpers import BaseTest


class TestAnalyzeApi(BaseTest):
    base_uri = "/api/analyze"

    def test_post_Report(self, client, auth_header, cleanup_report_item):
        """
        This test queries the /api/analyze/report-items endpoint with a POST request.
        It expects a valid data and a valid status-code
        """
        response = self.assert_post_ok(client, "report-items", auth_header=auth_header, json_data=cleanup_report_item)
        assert response.get_json()["title"] == cleanup_report_item["title"]

    def test_get_Reports(self, client, auth_header, cleanup_report_item):
        """
        This test queries the /api/analyze/report-items endpoint.
        It expects a valid data and a valid status-code
        """
        response = self.assert_get_ok(client, "report-items", auth_header)
        assert response.get_json()["total_count"] == 1
        items = response.get_json()["items"]
        assert len(items) == 1
        assert items[0]["title"] == cleanup_report_item["title"]
