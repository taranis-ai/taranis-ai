class TestWorkerApi:
    base_uri = "/api/worker"

    def test_worker_story_update(self, client, stories, cleanup_story_update_data, api_header):
        """
        This test queries the story update authenticated.
        It expects a valid data and a valid status-code
        """

        update_story_data = cleanup_story_update_data
        update_story_data["id"] = stories[0]

        response = client.post(
            f"{self.base_uri}/stories",
            json=update_story_data,
            headers=api_header,
        )

        assert response.status_code == 200
        result = response.get_json()
        assert result.get("message") == "Story updated Successful"
        assert result.get("id") == stories[0]

        response = client.get(f"{self.base_uri}/stories", headers=api_header, query_string={"story_id": stories[0]})

        assert response.status_code == 200
        assert response.get_json()[0].get("title") == update_story_data["title"]
        assert response.get_json()[0].get("id") == stories[0]


class TestWorkerStoryApi:
    base_uri = "/api/worker"

    def test_news_items_to_story(self, client, news_items, api_header):
        story = {
            "title": "Test title",
            "attributes": [{"key": "hey", "value": "hou"}],
            "news_items": news_items,
        }

        response = client.post(f"{self.base_uri}/stories", json=story, headers=api_header)

        assert response.status_code == 200
        assert response.get_json().get("message") == "Story added successfully"
