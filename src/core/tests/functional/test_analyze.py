from tests.functional.helpers import BaseTest


class TestAnalyzepi(BaseTest):
    base_uri = "/api/analyze"

    def test_get_Reports(self, client, auth_header):
        """
        This test queries the /api/analyze/report-items endpoint.
        It expects a valid data and a valid status-code
        """
        response = self.assert_get_ok(client, "report-items", auth_header)
        assert response.get_json()["total_count"] == 0
        assert response.get_json()["items"] == []
