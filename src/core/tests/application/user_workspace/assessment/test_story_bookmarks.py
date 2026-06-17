from uuid import uuid4

from tests.application.support.api_test_base import BaseTest


class TestStoryBookmarks(BaseTest):
    base_uri = "/api/assess"

    def _create_bookmark(self, client, auth_header, name: str):
        response = client.post(self.concat_url("bookmarks"), headers=auth_header, json={"name": name})
        assert response.status_code == 201
        return response.get_json()["id"]

    def _add_stories(self, client, auth_header, bookmark_id: str, story_ids: list[str]):
        response = client.post(self.concat_url(f"bookmarks/{bookmark_id}/stories"), headers=auth_header, json={"story_ids": story_ids})
        assert response.status_code == 200
        return response.get_json()

    def test_story_bookmarks_list_by_created_order(self, client, auth_header):
        prefix = f"Ordered {uuid4()}"
        first_response = client.post(self.concat_url("bookmarks"), headers=auth_header, json={"name": f"{prefix} first"})
        second_response = client.post(self.concat_url("bookmarks"), headers=auth_header, json={"name": f"{prefix} second"})

        assert first_response.status_code == 201
        assert second_response.status_code == 201
        first_payload = first_response.get_json()["bookmark"]
        second_payload = second_response.get_json()["bookmark"]

        list_response = client.get(self.concat_url("bookmarks"), headers=auth_header, query_string={"search": prefix})

        assert list_response.status_code == 200
        assert [item["id"] for item in list_response.get_json()["items"]] == [first_payload["id"], second_payload["id"]]

    def test_story_bookmarks_default_order_uses_created_not_updated(self, client, stories, auth_header):
        prefix = f"Created {uuid4()}"
        low_response = client.post(self.concat_url("bookmarks"), headers=auth_header, json={"name": f"{prefix} low"})
        high_response = client.post(self.concat_url("bookmarks"), headers=auth_header, json={"name": f"{prefix} high"})
        assert low_response.status_code == 201
        assert high_response.status_code == 201

        low_id = low_response.get_json()["id"]
        high_id = high_response.get_json()["id"]
        self._add_stories(client, auth_header, high_id, [stories[0]])

        list_response = client.get(self.concat_url("bookmarks"), headers=auth_header, query_string={"search": prefix})

        assert list_response.status_code == 200
        assert [item["id"] for item in list_response.get_json()["items"]] == [low_id, high_id]

    def test_story_bookmark_lifecycle(self, client, stories, auth_header):
        bookmark_id = self._create_bookmark(client, auth_header, f"Bookmark {uuid4()}")

        response = client.post(self.concat_url(f"bookmarks/{bookmark_id}/stories"), headers=auth_header, json={"story_ids": stories[:2]})
        assert response.status_code == 200
        assert response.get_json()["added"] == 2
        assert response.get_json()["story_count"] == 2

        duplicate_response = client.post(
            self.concat_url(f"bookmarks/{bookmark_id}/stories"), headers=auth_header, json={"story_ids": [stories[0]]}
        )
        assert duplicate_response.status_code == 200
        assert duplicate_response.get_json()["added"] == 0
        assert duplicate_response.get_json()["story_count"] == 2

        detail_response = client.get(self.concat_url(f"bookmarks/{bookmark_id}"), headers=auth_header)
        assert detail_response.status_code == 200
        detail = detail_response.get_json()
        assert detail["story_count"] == 2
        assert set(detail["story_ids"]) == set(stories[:2])
        assert {item["id"] for item in detail["stories"]} == set(stories[:2])

        remove_response = client.post(
            self.concat_url(f"bookmarks/{bookmark_id}/stories/remove"), headers=auth_header, json={"story_ids": [stories[0]]}
        )
        assert remove_response.status_code == 200
        assert remove_response.get_json()["removed"] == 1
        assert remove_response.get_json()["story_count"] == 1

        rename_response = client.patch(self.concat_url(f"bookmarks/{bookmark_id}"), headers=auth_header, json={"name": f"Renamed {uuid4()}"})
        assert rename_response.status_code == 200
        assert rename_response.get_json()["bookmark"]["story_count"] == 1

        delete_response = client.delete(self.concat_url(f"bookmarks/{bookmark_id}"), headers=auth_header)
        assert delete_response.status_code == 200

        missing_response = client.get(self.concat_url(f"bookmarks/{bookmark_id}"), headers=auth_header)
        assert missing_response.status_code == 404

        story_response = client.get(self.concat_url(f"stories/{stories[1]}"), headers=auth_header)
        assert story_response.status_code == 200

    def test_story_bookmarks_are_private_per_user(self, client, stories, auth_header, auth_header_user_permissions):
        bookmark_id = self._create_bookmark(client, auth_header, f"Private {uuid4()}")

        list_response = client.get(self.concat_url("bookmarks"), headers=auth_header_user_permissions)
        assert list_response.status_code == 200
        assert bookmark_id not in {item["id"] for item in list_response.get_json()["items"]}

        get_response = client.get(self.concat_url(f"bookmarks/{bookmark_id}"), headers=auth_header_user_permissions)
        assert get_response.status_code == 404

        add_response = client.post(
            self.concat_url(f"bookmarks/{bookmark_id}/stories"), headers=auth_header_user_permissions, json={"story_ids": [stories[0]]}
        )
        assert add_response.status_code == 404

        delete_response = client.delete(self.concat_url(f"bookmarks/{bookmark_id}"), headers=auth_header_user_permissions)
        assert delete_response.status_code == 404

    def test_story_bookmark_duplicate_names_are_rejected(self, client, auth_header):
        name = f"Duplicate {uuid4()}"
        self._create_bookmark(client, auth_header, name)

        response = client.post(self.concat_url("bookmarks"), headers=auth_header, json={"name": name})

        assert response.status_code == 409
        assert response.get_json() == {"error": "A bookmark collection with this name already exists"}

    def test_story_bookmark_rejects_missing_stories(self, client, auth_header):
        bookmark_id = self._create_bookmark(client, auth_header, f"Missing story {uuid4()}")

        response = client.post(
            self.concat_url(f"bookmarks/{bookmark_id}/stories"), headers=auth_header, json={"story_ids": ["missing-story"]}
        )

        assert response.status_code == 404
        assert response.get_json() == {"error": "Story not found"}

    def test_story_bookmark_remove_absent_story_is_idempotent(self, client, stories, auth_header):
        bookmark_id = self._create_bookmark(client, auth_header, f"Idempotent {uuid4()}")
        add_response = client.post(
            self.concat_url(f"bookmarks/{bookmark_id}/stories"),
            headers=auth_header,
            json={"story_ids": [stories[0]]},
        )
        assert add_response.status_code == 200

        response = client.post(
            self.concat_url(f"bookmarks/{bookmark_id}/stories/remove"), headers=auth_header, json={"story_ids": [stories[1]]}
        )

        assert response.status_code == 200
        assert response.get_json()["removed"] == 0
        assert response.get_json()["story_count"] == 1
