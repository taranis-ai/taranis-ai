from tests.conftest import api_header
from tests.functional.conftest import wordlist_bot_result
from tests.functional.helpers import BaseTest


class TestBotsApi(BaseTest):
    base_uri = "/api/bots"

    def deepmerge(self, base: dict, update: dict) -> dict:
        result = base.copy()
        for key, value in update.items():
            if key in ("attributes") and key in result:
                # merge lists instead of overwriting
                result[key] = result[key] + value
            else:
                # overwrite other keys
                result[key] = value
        return result

    def test_story_update(self, client, stories, cleanup_story_update_data, api_header):
        """
        This test queries the story update authenticated.
        It expects a valid data and a valid status-code
        """
        response = client.get(f"{self.base_uri}/story/{stories[0]}", headers=api_header)
        self.assert_json_ok(response)
        current_story_data = response.get_json()

        # Update current_story with with the cleanup_story_update_data
        update_story_data = self.deepmerge(current_story_data, cleanup_story_update_data)

        assert len(update_story_data["attributes"]) == len(cleanup_story_update_data["attributes"]) + 1
        check_attributes = sorted(update_story_data["attributes"], key=lambda d: d["key"])
        expected_attributes = sorted(
            cleanup_story_update_data["attributes"] + [{"key": "TLP", "value": "clear"}],
            key=lambda d: d["key"],
        )
        assert check_attributes == expected_attributes

        response = client.put(f"{self.base_uri}/story/{stories[0]}", json=update_story_data, headers=api_header)
        story_id = response.get_json().get("id")

        assert response.status_code == 200
        assert story_id == stories[0], "Response ID should match request ID"

    def test_old_format_attribute_update(self, client, stories, api_header):
        """
        This test queries the story update authenticated.
        It expects a valid data and a valid status-code
        """
        response = client.patch(
            f"{self.base_uri}/story/{stories[0]}/attributes", json=[{"key": "tech", "value": "in_progress"}], headers=api_header
        )
        assert response.status_code == 200

    def test_new_format_attribute_update(self, client, stories, api_header):
        """
        This test queries the story update authenticated.
        It expects a valid data and a valid status-code
        """
        response = client.patch(
            f"{self.base_uri}/story/{stories[0]}/attributes",
            json={"point": {"key": "point", "value": "making"}, "tree": {"key": "tree", "value": "green"}},
            headers=api_header,
        )
        assert response.status_code == 200

    def test_check_updated_story(self, client, stories, cleanup_story_update_data, auth_header):
        """Check if the update was successful"""
        response = client.get(f"api/assess/story/{stories[0]}", headers=auth_header)

        assert response.status_code == 200
        assert response.get_json().get("important") == cleanup_story_update_data["important"]
        assert response.get_json().get("read") == cleanup_story_update_data["read"]
        assert response.get_json().get("title") == cleanup_story_update_data["title"]
        assert response.get_json().get("description") == cleanup_story_update_data["description"]
        assert response.get_json().get("comments") == cleanup_story_update_data["comments"]
        assert response.get_json().get("summary") == cleanup_story_update_data["summary"]

        attributes = sorted(response.get_json()["attributes"], key=lambda d: d["key"])
        expected_attributes = sorted(
            cleanup_story_update_data["attributes"]
            + [
                {"key": "tech", "value": "in_progress"},
                {"key": "TLP", "value": "clear"},
                {"key": "point", "value": "making"},
                {"key": "tree", "value": "green"},
            ],
            key=lambda d: d["key"],
        )

        assert attributes == expected_attributes


class TestTaggingBotsResults(BaseTest):
    base_uri = "/api/tasks"

    def test_check_story_tags_after_wordlist_bot(self, client, stories, auth_header, wordlist_bot_result, applied_wordlist):
        for story_id in stories:
            response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
            assert response.status_code == 200

            structured_tags = {tag["name"]: tag["tag_type"] for tag in response.get_json().get("tags", [])}

            expected_tags = wordlist_bot_result["result"]["result"].get(story_id, {})
            assert structured_tags == expected_tags

            attr_by_key = {a.get("key"): a.get("value") for a in response.get_json().get("attributes", [])}
            assert attr_by_key["TLP"] == "clear"
            assert str(attr_by_key["WORDLIST_BOT"]).startswith("bot_id=")

    def test_check_story_tags_after_ioc_bot(
        self,
        client,
        stories,
        auth_header,
        wordlist_bot_result,
        ioc_bot_result,
        applied_wordlist,
        applied_ioc,
    ):
        for story_id in stories:
            response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
            assert response.status_code == 200

            structured_tags = {tag["name"]: tag["tag_type"] for tag in response.get_json().get("tags", [])}

            expected = {}
            expected |= wordlist_bot_result["result"]["result"].get(story_id, {})
            expected |= ioc_bot_result["result"]["result"].get(story_id, {})

            assert structured_tags == expected

    def test_check_story_tags_after_nlp_bot(
        self,
        client,
        stories,
        auth_header,
        wordlist_bot_result,
        ioc_bot_result,
        nlp_bot_result,
        applied_wordlist,
        applied_ioc,
        applied_nlp,
    ):
        for story_id in stories:
            response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
            assert response.status_code == 200

            structured_tags = {tag["name"]: tag["tag_type"] for tag in response.get_json().get("tags", [])}

            expected = {}
            expected |= wordlist_bot_result["result"]["result"].get(story_id, {})
            expected |= ioc_bot_result["result"]["result"].get(story_id, {})
            expected |= nlp_bot_result["result"]["result"].get(story_id, {})

            assert structured_tags == expected

            attr_by_key = {a.get("key"): a.get("value") for a in response.get_json().get("attributes", [])}
            assert attr_by_key["TLP"] == "clear"
            assert attr_by_key["WORDLIST_BOT"].startswith("bot_id=")
            assert attr_by_key["IOC_BOT"].startswith("bot_id=")
            assert attr_by_key["NLP_BOT"].startswith("bot_id=")
