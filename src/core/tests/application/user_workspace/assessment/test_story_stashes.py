from uuid import uuid4

from tests.application.support.api_test_base import BaseTest


class TestStoryStashes(BaseTest):
    base_uri = "/api/assess"

    def _create_stash(self, client, auth_header, name: str):
        response = client.post(self.concat_url("stashes"), headers=auth_header, json={"name": name})
        assert response.status_code == 201
        return response.get_json()["id"]

    def test_story_stash_lifecycle(self, client, stories, auth_header):
        stash_id = self._create_stash(client, auth_header, f"Stash {uuid4()}")

        response = client.post(self.concat_url(f"stashes/{stash_id}/stories"), headers=auth_header, json={"story_ids": stories[:2]})
        assert response.status_code == 200
        assert response.get_json()["added"] == 2
        assert response.get_json()["story_count"] == 2

        duplicate_response = client.post(
            self.concat_url(f"stashes/{stash_id}/stories"), headers=auth_header, json={"story_ids": [stories[0]]}
        )
        assert duplicate_response.status_code == 200
        assert duplicate_response.get_json()["added"] == 0
        assert duplicate_response.get_json()["story_count"] == 2

        detail_response = client.get(self.concat_url(f"stashes/{stash_id}"), headers=auth_header)
        assert detail_response.status_code == 200
        detail = detail_response.get_json()
        assert detail["story_count"] == 2
        assert set(detail["story_ids"]) == set(stories[:2])
        assert {item["id"] for item in detail["stories"]} == set(stories[:2])

        remove_response = client.post(
            self.concat_url(f"stashes/{stash_id}/stories/remove"), headers=auth_header, json={"story_ids": [stories[0]]}
        )
        assert remove_response.status_code == 200
        assert remove_response.get_json()["removed"] == 1
        assert remove_response.get_json()["story_count"] == 1

        rename_response = client.patch(self.concat_url(f"stashes/{stash_id}"), headers=auth_header, json={"name": f"Renamed {uuid4()}"})
        assert rename_response.status_code == 200
        assert rename_response.get_json()["stash"]["story_count"] == 1

        delete_response = client.delete(self.concat_url(f"stashes/{stash_id}"), headers=auth_header)
        assert delete_response.status_code == 200

        missing_response = client.get(self.concat_url(f"stashes/{stash_id}"), headers=auth_header)
        assert missing_response.status_code == 404

        story_response = client.get(self.concat_url(f"stories/{stories[1]}"), headers=auth_header)
        assert story_response.status_code == 200

    def test_story_stashes_are_private_per_user(self, client, stories, auth_header, auth_header_user_permissions):
        stash_id = self._create_stash(client, auth_header, f"Private {uuid4()}")

        list_response = client.get(self.concat_url("stashes"), headers=auth_header_user_permissions)
        assert list_response.status_code == 200
        assert stash_id not in {item["id"] for item in list_response.get_json()["items"]}

        get_response = client.get(self.concat_url(f"stashes/{stash_id}"), headers=auth_header_user_permissions)
        assert get_response.status_code == 404

        add_response = client.post(
            self.concat_url(f"stashes/{stash_id}/stories"), headers=auth_header_user_permissions, json={"story_ids": [stories[0]]}
        )
        assert add_response.status_code == 404

        delete_response = client.delete(self.concat_url(f"stashes/{stash_id}"), headers=auth_header_user_permissions)
        assert delete_response.status_code == 404

    def test_story_stash_duplicate_names_are_rejected(self, client, auth_header):
        name = f"Duplicate {uuid4()}"
        self._create_stash(client, auth_header, name)

        response = client.post(self.concat_url("stashes"), headers=auth_header, json={"name": name})

        assert response.status_code == 409
        assert response.get_json() == {"error": "A stash with this name already exists"}

    def test_story_stash_rejects_missing_stories(self, client, auth_header):
        stash_id = self._create_stash(client, auth_header, f"Missing story {uuid4()}")

        response = client.post(self.concat_url(f"stashes/{stash_id}/stories"), headers=auth_header, json={"story_ids": ["missing-story"]})

        assert response.status_code == 404
        assert response.get_json() == {"error": "Story not found"}

    def test_story_stash_remove_absent_story_is_idempotent(self, client, stories, auth_header):
        stash_id = self._create_stash(client, auth_header, f"Idempotent {uuid4()}")
        client.post(self.concat_url(f"stashes/{stash_id}/stories"), headers=auth_header, json={"story_ids": [stories[0]]})

        response = client.post(self.concat_url(f"stashes/{stash_id}/stories/remove"), headers=auth_header, json={"story_ids": [stories[1]]})

        assert response.status_code == 200
        assert response.get_json()["removed"] == 0
        assert response.get_json()["story_count"] == 1
