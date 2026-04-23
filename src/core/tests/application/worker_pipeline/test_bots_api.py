from tests.application.support.api_test_base import BaseTest


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

    def test_story_attribute_update_is_persisted(self, client, stories, api_header, auth_header):
        misp_event_uuid = "320d4589-cd71-4722-aa28-ea5530e99830"
        story_id = stories[1]

        response = client.patch(
            f"{self.base_uri}/story/{story_id}/attributes",
            json={"misp_event_uuid": {"key": "misp_event_uuid", "value": misp_event_uuid}},
            headers=api_header,
        )
        assert response.status_code == 200

        response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
        self.assert_json_ok(response)

        attr_by_key = {attr["key"]: attr["value"] for attr in response.get_json()["attributes"]}
        assert attr_by_key["misp_event_uuid"] == misp_event_uuid

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

            expected_tags = {}
            for news_item in response.get_json().get("news_items", []):
                expected_tags |= wordlist_bot_result["result"].get(news_item["id"], {})
            assert structured_tags == expected_tags

            attr_by_key = {a.get("key"): a.get("value") for a in response.get_json().get("attributes", [])}
            assert attr_by_key["TLP"] == "clear"
            assert str(attr_by_key["WORDLIST_BOT"]).startswith("worker_id=")

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
            for news_item in response.get_json().get("news_items", []):
                expected |= wordlist_bot_result["result"].get(news_item["id"], {})
                expected |= ioc_bot_result["result"].get(news_item["id"], {})

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
            for news_item in response.get_json().get("news_items", []):
                expected |= wordlist_bot_result["result"].get(news_item["id"], {})
                expected |= ioc_bot_result["result"].get(news_item["id"], {})
                expected |= nlp_bot_result["result"].get(news_item["id"], {})

            assert structured_tags == expected

            attr_by_key = {a.get("key"): a.get("value") for a in response.get_json().get("attributes", [])}
            assert attr_by_key["TLP"] == "clear"
            assert attr_by_key["WORDLIST_BOT"].startswith("worker_id=")
            assert attr_by_key["IOC_BOT"].startswith("worker_id=")
            assert attr_by_key["NLP_BOT"].startswith("worker_id=")


class TestConnectorTaskResults(BaseTest):
    base_uri = "/api/tasks"

    def build_misp_connector_result(self, story_id: str, misp_event_uuid: str, news_item_ids: list[str]) -> dict:
        return {
            "task_id": "connector_task_320d4589-cd71-4722-aa28-ea5530e99830",
            "status": "SUCCESS",
            "result": {
                "connector_id": "74981521-4ba7-4216-b9ca-ebc00ffec29c",
                "connector_type": "MISP_CONNECTOR",
                "action": "synced",
                "message": "Story synced to MISP",
                "sync_results": [
                    {
                        "type": "misp_sync_story",
                        "version": 1,
                        "story_id": story_id,
                        "misp_event_uuid": misp_event_uuid,
                        "news_item_ids_to_mark_external": news_item_ids,
                    }
                ],
            },
            "task": "connector_task",
        }

    def build_misp_connector_proposal_result(self, story_id: str, misp_event_uuid: str) -> dict:
        return {
            "task_id": "connector_task_proposal_320d4589-cd71-4722-aa28-ea5530e99830",
            "status": "SUCCESS",
            "result": {
                "connector_id": "74981521-4ba7-4216-b9ca-ebc00ffec29c",
                "connector_type": "MISP_CONNECTOR",
                "action": "proposed",
                "message": "1 proposals submitted to MISP",
                "sync_results": [],
            },
            "task": "connector_task",
        }

    def test_misp_connector_result_updates_story_through_task_endpoint(self, client, stories, auth_header, api_header):
        story_id = stories[2]
        misp_event_uuid = "320d4589-cd71-4722-aa28-ea5530e99830"

        response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
        self.assert_json_ok(response)
        original_story = response.get_json()
        news_item_id = original_story["news_items"][0]["id"]

        assert original_story["last_change"] == "internal"
        assert original_story["news_items"][0]["last_change"] == "internal"

        response = client.post(
            self.base_uri,
            json=self.build_misp_connector_result(story_id, misp_event_uuid, [news_item_id]),
            headers=api_header,
        )
        assert response.status_code == 200
        assert response.get_json()["status"] == "SUCCESS"

        response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
        self.assert_json_ok(response)
        updated_story = response.get_json()

        attr_by_key = {attr["key"]: attr["value"] for attr in updated_story["attributes"]}
        assert attr_by_key["misp_event_uuid"] == misp_event_uuid
        assert updated_story["last_change"] == "external"
        assert updated_story["news_items"][0]["last_change"] == "external"
        assert updated_story["revision_count"] == original_story["revision_count"] + 1

    def test_misp_connector_result_is_idempotent(self, client, stories, auth_header, api_header):
        story_id = stories[2]
        misp_event_uuid = "83c9901c-a767-4dab-928c-c61e09765f94"

        response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
        self.assert_json_ok(response)
        story = response.get_json()
        news_item_id = story["news_items"][0]["id"]
        payload = self.build_misp_connector_result(story_id, misp_event_uuid, [news_item_id])

        first_response = client.post(self.base_uri, json=payload, headers=api_header)
        assert first_response.status_code == 200

        response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
        self.assert_json_ok(response)
        story_after_first_post = response.get_json()

        second_response = client.post(self.base_uri, json=payload, headers=api_header)
        assert second_response.status_code == 200

        response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
        self.assert_json_ok(response)
        story_after_second_post = response.get_json()

        attr_by_key = {attr["key"]: attr["value"] for attr in story_after_second_post["attributes"]}
        assert attr_by_key["misp_event_uuid"] == misp_event_uuid
        assert story_after_second_post["revision_count"] == story_after_first_post["revision_count"]

    def test_misp_connector_proposal_result_is_stored_with_summary(self, client, stories, auth_header, api_header):
        story_id = stories[2]
        task_id = "connector_task_proposal_320d4589-cd71-4722-aa28-ea5530e99830"
        misp_event_uuid = "83c9901c-a767-4dab-928c-c61e09765f94"

        response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
        self.assert_json_ok(response)
        original_story = response.get_json()

        response = client.post(
            self.base_uri,
            json=self.build_misp_connector_proposal_result(story_id, misp_event_uuid),
            headers=api_header,
        )
        assert response.status_code == 200

        response = client.get(f"/api/tasks/{task_id}", headers=api_header)
        self.assert_json_ok(response)
        task_result = response.get_json()["result"]

        assert task_result["action"] == "proposed"
        assert task_result["message"] == "1 proposals submitted to MISP"
        assert task_result["sync_results"] == []

        response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
        self.assert_json_ok(response)
        updated_story = response.get_json()

        assert updated_story["revision_count"] == original_story["revision_count"]

    def test_unknown_connector_result_is_logged_and_ignored(self, client, stories, auth_header, api_header, caplog):
        import logging

        story_id = stories[0]
        response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
        self.assert_json_ok(response)
        original_story = response.get_json()

        caplog.set_level(logging.WARNING)
        response = client.post(
            self.base_uri,
            json={
                "task_id": "connector_task_unknown",
                "status": "SUCCESS",
                "result": {
                    "connector_id": "74981521-4ba7-4216-b9ca-ebc00ffec29c",
                    "connector_type": "MISP_CONNECTOR",
                    "action": "mixed",
                    "message": "Connector finished with mixed results",
                    "sync_results": [{"type": "unknown_connector_result"}],
                },
                "task": "connector_task",
            },
            headers=api_header,
        )
        assert response.status_code == 200

        response = client.get(f"/api/assess/story/{story_id}", headers=auth_header)
        self.assert_json_ok(response)
        updated_story = response.get_json()

        assert updated_story["revision_count"] == original_story["revision_count"]
        assert "Unsupported MISP sync payload type: unknown_connector_result" in caplog.text

    def test_malformed_internal_result_is_rejected(self, app, caplog):
        import logging

        from core.service.misp_story_sync import apply_misp_sync_story_result

        caplog.set_level(logging.ERROR)
        with app.app_context():
            assert (
                apply_misp_sync_story_result(
                    {
                        "type": "misp_sync_story",
                        "story_id": "story-123",
                        "misp_event_uuid": "320d4589-cd71-4722-aa28-ea5530e99830",
                        "news_item_ids_to_mark_external": "news-1",
                    }
                )
                is False
            )

        assert "news_item_ids_to_mark_external must be a list of non-empty strings" in caplog.text
