from tests.functional.helpers import BaseTest


class TestWorkerApi(BaseTest):
    base_uri = "/api/worker"

    def test_update_story_tags(self, client, stories, api_header):
        response = self.assert_put_ok(client, "tags", {stories[0]: ["abc", "def"], stories[1]: ["foo", "bar"]}, api_header)
        print(response.get_json())
