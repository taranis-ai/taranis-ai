class TestWorkerApi:
    base_uri = "/api/worker"

    def test_worker_story_update(self, client, cleanup_story_update_data, api_header):
        """
        This test queries the story update authenticated.
        It expects a valid data and a valid status-code
        """
        story_attribute_key = "rt_id"
        cleanup_story_update_data["title"] = "Updated using a special endpoint"
        response = client.post(
            f"{self.base_uri}/stories",
            json=cleanup_story_update_data,
            query_string={"story_attribute_key": story_attribute_key},
            headers=api_header,
        )

        assert response.status_code == 200

    def test_update_result(self, client, stories, api_header):
        response = client.get(f"{self.base_uri}/stories", headers=api_header, query_string={"story_id": stories[0]})

        assert response.status_code == 200
        assert response.get_json()[0].get("title") == "Updated using a special endpoint"
        assert response.get_json()[0].get("id") == stories[0]

    def test_news_items_to_story(self, client, news_items, api_header):
        news_items[0]["id"] = "dc11231e-449a-425a-a640-43c4f9ee7759"
        news_items[1]["id"] = "dc11231e-449a-425a-a640-43c4f9ee7754"
        news_items[0]["hash"] = "82e6e99403686a1072d0fb2013901b843a6725ba8ac4266270f62b7614ec1adg"
        news_items[1]["hash"] = "82e6e99403686a1072d0fb2013901b843a6725ba8ac4266270f62b7614ec1adh"
        story = {
            "title": "Test title",
            "attributes": [{"key": "hey", "value": "hou"}],
            "news_items": news_items,
        }

        response = client.post(f"{self.base_uri}/stories", json=story, headers=api_header)

        assert response.status_code == 200
        assert response.get_json().get("message") == "Story added successfully"
