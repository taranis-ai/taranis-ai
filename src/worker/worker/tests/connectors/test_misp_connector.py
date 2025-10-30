import pytest
import json
import worker.connectors as connectors
from worker.flows.connector_task_flow import drop_utf16_surrogates
from worker.config import Config


@pytest.fixture
def core_mock(requests_mock, stories):
    from worker.tests.misp_connector_test_data import misp_connector

    requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories?story_id=ed13a0b1-4f5f-4c43-bdf2-820ee0d43448", json=[stories[11]])
    requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/connectors/74981521-4ba7-4216-b9ca-ebc00ffec29c", json=misp_connector)
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/connectors/last-change", json={})
    requests_mock.patch(f"{Config.TARANIS_CORE_URL}/bots/story/ed13a0b1-4f5f-4c43-bdf2-820ee0d43448/attributes", json={})
    requests_mock.get("https://test.misp.test/servers/getVersion", json={"version": "2.5.10"})
    requests_mock.get("https://test.misp.test/servers/getPyMISPVersion.json", json={"version": "2.5.10"})
    requests_mock.get(
        "https://test.misp.test/users/view/me",
        json={
            "Role": {},
            "UserSetting": {"items": "test"},
        },
    )
    requests_mock.post("https://test.misp.test/events/add", json={"Event": {"id": "49", "info": "Test Event"}})


def test_news_item_object_keys_completeness(news_item_template):
    """Test that the object data keys match the template keys"""
    object_data = connectors.MISPConnector.get_news_item_object_dict()

    template_keys = set(news_item_template["attributes"].keys())
    object_data_keys = set(object_data.keys())

    missing_keys = template_keys - object_data_keys
    extra_keys = object_data_keys - template_keys

    assert len(missing_keys) == 0, f"Missing keys in object_data: {missing_keys}"
    assert len(extra_keys) == 0, f"Extra keys in object_data: {extra_keys}"
    assert template_keys == object_data_keys, "Object data keys do not match the template"


def test_story_object_completion(story_template):
    """Test that the object data keys match the template keys"""
    object_data = connectors.MISPConnector.get_story_object_dict()

    template_keys = set(story_template["attributes"].keys())
    object_data_keys = set(object_data.keys())

    missing_keys = template_keys - object_data_keys
    extra_keys = object_data_keys - template_keys

    assert len(missing_keys) == 0, f"Missing keys in object_data: {missing_keys}"
    assert len(extra_keys) == 0, f"Extra keys in object_data: {extra_keys}"
    assert template_keys == object_data_keys, "Object data keys do not match the template"


def test_story_utf8_decoding_mock(story_get_by_id_mock):
    """Test that UTF-16 surrogates are properly cleaned from story data"""
    from worker.core_api import CoreApi
    
    core_api = CoreApi()
    stories_raw = core_api.get_stories({"story_id": "11"})
    
    # Apply the same cleaning as connector_task_flow
    story_json = json.dumps(stories_raw)
    cleaned_json = drop_utf16_surrogates(story_json)
    cleaned_stories = json.loads(cleaned_json)
    
    surrogate_story = cleaned_stories[0]
    assert surrogate_story["summary"] == "Following some utf 16 chars  and  and "
    assert surrogate_story["news_items"][0]["content"] == "Following some utf 16 chars "


def test_story_utf8_decoding(stories):
    """Test that UTF-16 surrogates are dropped from story JSON"""
    story_json = json.dumps(stories)
    cleaned_json_str = drop_utf16_surrogates(story_json)
    result = json.loads(cleaned_json_str)
    cleaned_story = result[10]
    assert cleaned_story["summary"] == "Following some utf 16 chars  and  and "


def test_drop_utf16_surrogates_edge_cases():
    """Test drop_utf16_surrogates for various edge cases."""

    # Strings containing \n, \t, and " should be preserved.
    input_special = 'Line1\nLine2\t"Quoted text"'
    cleaned_special = drop_utf16_surrogates(input_special)
    assert cleaned_special == input_special, 'Special characters (\\n, \\t, ") modified incorrectly'

    # An empty string should be returned as an empty string.
    input_empty = ""
    cleaned_empty = drop_utf16_surrogates(input_empty)
    assert cleaned_empty == "", "Empty string not handled correctly"

    # A pure ASCII string remains unaltered.
    input_ascii = "This is a simple ASCII string."
    cleaned_ascii = drop_utf16_surrogates(input_ascii)
    assert cleaned_ascii == input_ascii, "ASCII string altered unexpectedly"


def test_connector_story_processing(core_mock, caplog):
    """Test MISP connector processing with mocked Core API (adapted for Prefect flows)"""
    import logging

    # Set the logging level to ERROR to capture only error logs and fail properly
    caplog.set_level(logging.ERROR, logger="root")

    from worker.flows.connector_task_flow import get_connector_config, get_connector_instance, get_stories_by_id, execute_connector

    # Get connector config and instance (mimics Prefect flow)
    connector_config, connector_type = get_connector_config("74981521-4ba7-4216-b9ca-ebc00ffec29c")
    connector = get_connector_instance(connector_type)
    
    # Get stories with UTF-16 surrogate cleaning
    stories = get_stories_by_id(["ed13a0b1-4f5f-4c43-bdf2-820ee0d43448"])
    
    # Execute connector
    result = execute_connector(connector, connector_config, stories)

    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert not errors, "Unexpected log errors:\n" + "\n".join(f"{r.levelname}: {r.message}" for r in errors)

    assert result is None
