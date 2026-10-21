from uuid import uuid4

from tests.application.support.api_test_base import BaseTest
from tests.application.support.builders import build_news_item_payload, create_story


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

    def test_story_bookmarks_list_by_position_order(self, client, auth_header):
        prefix = f"Ordered {uuid4()}"
        first_response = client.post(self.concat_url("bookmarks"), headers=auth_header, json={"name": f"{prefix} first"})
        second_response = client.post(self.concat_url("bookmarks"), headers=auth_header, json={"name": f"{prefix} second"})

        assert first_response.status_code == 201
        assert second_response.status_code == 201
        first_payload = first_response.get_json()["bookmark"]
        second_payload = second_response.get_json()["bookmark"]

        list_response = client.get(self.concat_url("bookmarks"), headers=auth_header, query_string={"search": prefix})

        assert list_response.status_code == 200
        items = list_response.get_json()["items"]
        assert [item["id"] for item in items] == [first_payload["id"], second_payload["id"]]
        assert [item["position"] for item in items] == [first_payload["position"], second_payload["position"]]
        assert second_payload["position"] == first_payload["position"] + 1

    def test_story_bookmarks_default_order_uses_position_not_updated(self, client, stories, auth_header):
        prefix = f"Position {uuid4()}"
        low_response = client.post(self.concat_url("bookmarks"), headers=auth_header, json={"name": f"{prefix} low"})
        high_response = client.post(self.concat_url("bookmarks"), headers=auth_header, json={"name": f"{prefix} high"})
        assert low_response.status_code == 201
        assert high_response.status_code == 201

        low_id = low_response.get_json()["id"]
        high_id = high_response.get_json()["id"]
        reorder_response = client.patch(self.concat_url("bookmarks/order"), headers=auth_header, json={"bookmark_ids": [high_id, low_id]})
        assert reorder_response.status_code == 200
        self._add_stories(client, auth_header, low_id, [stories[0]])

        list_response = client.get(self.concat_url("bookmarks"), headers=auth_header, query_string={"search": prefix})

        assert list_response.status_code == 200
        items = list_response.get_json()["items"]
        assert [item["id"] for item in items] == [high_id, low_id]
        assert [item["position"] for item in items] == [0, 1]

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

        reorder_response = client.patch(
            self.concat_url("bookmarks/order"), headers=auth_header_user_permissions, json={"bookmark_ids": [bookmark_id]}
        )
        assert reorder_response.status_code == 404

        delete_response = client.delete(self.concat_url(f"bookmarks/{bookmark_id}"), headers=auth_header_user_permissions)
        assert delete_response.status_code == 404

    def test_story_bookmark_duplicate_names_are_rejected(self, client, auth_header):
        name = f"Duplicate {uuid4()}"
        self._create_bookmark(client, auth_header, name)

        response = client.post(self.concat_url("bookmarks"), headers=auth_header, json={"name": name})

        assert response.status_code == 409
        assert response.get_json() == {"error": "A bookmark collection with this name already exists"}

    def test_explicit_default_survives_reordering_and_deleted_default_recovers(self, client, stories, auth_header):
        first = self._create_bookmark(client, auth_header, f"Default {uuid4()}")
        second = self._create_bookmark(client, auth_header, f"Other {uuid4()}")
        response = client.patch(self.concat_url(f"bookmarks/{first}"), headers=auth_header, json={"is_default": True})
        assert response.status_code == 200
        assert response.get_json()["bookmark"]["is_default"] is True
        client.patch(self.concat_url("bookmarks/order"), headers=auth_header, json={"bookmark_ids": [second, first]})

        saved = client.post(self.concat_url("bookmarks/quick-save"), headers=auth_header, json={"story_ids": [stories[0]]})
        assert saved.status_code == 200
        assert saved.get_json()["bookmark"]["id"] == first
        assert saved.get_json()["added_story_ids"] == [stories[0]]
        repeated = client.post(self.concat_url("bookmarks/quick-save"), headers=auth_header, json={"story_ids": [stories[0]]})
        assert repeated.get_json()["added_story_ids"] == []

        client.delete(self.concat_url(f"bookmarks/{first}"), headers=auth_header)
        recovered = client.post(self.concat_url("bookmarks/quick-save"), headers=auth_header, json={"story_ids": [stories[0]]})
        assert recovered.status_code == 200
        assert recovered.get_json()["bookmark"]["name"] == "Bookmarks"
        assert recovered.get_json()["bookmark"]["is_default"] is True
        assert recovered.get_json()["bookmark"]["id"] != second

    def test_membership_changes_are_atomic_and_leave_unmentioned_collections_unchanged(self, client, stories, auth_header):
        first = self._create_bookmark(client, auth_header, f"First {uuid4()}")
        second = self._create_bookmark(client, auth_header, f"Second {uuid4()}")
        self._add_stories(client, auth_header, first, stories[:2])
        self._add_stories(client, auth_header, second, [stories[0]])
        payload = {"story_ids": stories[:2], "remove_bookmark_ids": [first], "new_collection_name": f"New {uuid4()}"}
        response = client.post(self.concat_url("bookmarks/memberships"), headers=auth_header, json=payload)
        assert response.status_code == 200
        assert client.get(self.concat_url(f"bookmarks/{first}"), headers=auth_header).get_json()["story_ids"] == []
        assert client.get(self.concat_url(f"bookmarks/{second}"), headers=auth_header).get_json()["story_ids"] == [stories[0]]
        created = client.get(self.concat_url("bookmarks"), headers=auth_header, query_string={"search": payload["new_collection_name"]})
        assert set(created.get_json()["items"][0]["story_ids"]) == set(stories[:2])

        payload.update(bookmark_ids=[first], remove_bookmark_ids=[second])
        conflict = client.post(self.concat_url("bookmarks/memberships"), headers=auth_header, json=payload)
        assert conflict.status_code == 409
        assert client.get(self.concat_url(f"bookmarks/{first}"), headers=auth_header).get_json()["story_ids"] == []
        assert client.get(self.concat_url(f"bookmarks/{second}"), headers=auth_header).get_json()["story_ids"] == [stories[0]]

    def test_membership_and_saved_state_are_private(self, client, stories, auth_header, auth_header_user_permissions):
        private = self._create_bookmark(client, auth_header, f"Private membership {uuid4()}")
        self._add_stories(client, auth_header, private, [stories[0]])
        for path in (f"stories/{stories[0]}", "stories"):
            query = {"story_ids": [stories[0]]} if path == "stories" else {}
            response = client.get(self.concat_url(path), headers=auth_header, query_string=query)
            assert response.status_code == 200
            story = response.get_json()["items"][0] if path == "stories" else response.get_json()
            assert story["bookmarked"] is True
            other = client.get(self.concat_url(path), headers=auth_header_user_permissions, query_string=query)
            assert other.status_code == 200
            story = other.get_json()["items"][0] if path == "stories" else other.get_json()
            assert story["bookmarked"] is False
        response = client.post(
            self.concat_url("bookmarks/memberships"),
            headers=auth_header_user_permissions,
            json={"story_ids": [stories[0]], "bookmark_ids": [private], "new_collection_name": f"Never created {uuid4()}"},
        )
        assert response.status_code == 404
        default = client.patch(self.concat_url(f"bookmarks/{private}"), headers=auth_header_user_permissions, json={"is_default": True})
        assert default.status_code == 404

    def test_story_bookmark_rejects_missing_stories(self, client, auth_header):
        bookmark_id = self._create_bookmark(client, auth_header, f"Missing story {uuid4()}")

        response = client.post(
            self.concat_url(f"bookmarks/{bookmark_id}/stories"), headers=auth_header, json={"story_ids": ["missing-story"]}
        )

        assert response.status_code == 404
        assert response.get_json() == {"error": "One of the provided stories was not found"}

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

    def test_ungroup_replaces_bookmarked_story_with_created_stories(self, app, client, auth_header, fake_source):
        with app.app_context():
            story = create_story(
                news_items=[
                    build_news_item_payload(source_id=fake_source, title="First bookmarked item"),
                    build_news_item_payload(source_id=fake_source, title="Second bookmarked item"),
                ]
            )
            source_story_id = story.id

        bookmark_id = self._create_bookmark(client, auth_header, f"Ungroup {uuid4()}")
        self._add_stories(client, auth_header, bookmark_id, [source_story_id])

        response = client.put(self.concat_url("stories/ungroup"), headers=auth_header, json=[source_story_id])

        assert response.status_code == 200
        detail_response = client.get(self.concat_url(f"bookmarks/{bookmark_id}"), headers=auth_header)
        assert detail_response.status_code == 200
        detail = detail_response.get_json()
        assert detail["story_count"] == 2
        assert source_story_id not in detail["story_ids"]
        assert {item["title"] for item in detail["stories"]} == {"First bookmarked item", "Second bookmarked item"}
