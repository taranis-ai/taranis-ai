import json

import pytest

from worker.config import Config
from worker.connectors import base_misp_builder, connector_tasks
from worker.connectors.misp_connector import MispConnector
from worker.core_api import CoreApi


@pytest.fixture
def misp_connector_core_mock(requests_mock, stories):
    from worker.tests.misp_connector_test_data import misp_connector

    requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories?story_id=ed13a0b1-4f5f-4c43-bdf2-820ee0d43448", json=[stories[11]])
    requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/connectors/74981521-4ba7-4216-b9ca-ebc00ffec29c", json=misp_connector)
    requests_mock.put(f"{Config.TARANIS_CORE_URL}/worker/misp/last-change", json={})
    requests_mock.patch(f"{Config.TARANIS_CORE_URL}/bots/story/ed13a0b1-4f5f-4c43-bdf2-820ee0d43448/attributes", json={})


@pytest.fixture
def misp_api_mock(requests_mock):
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
    object_data = base_misp_builder.get_news_item_object_dict_empty()

    template_keys = set(news_item_template["attributes"].keys())
    object_data_keys = set(object_data.keys())

    missing_keys = template_keys - object_data_keys
    extra_keys = object_data_keys - template_keys

    assert len(missing_keys) == 0, f"Missing keys in object_data: {missing_keys}"
    assert len(extra_keys) == 0, f"Extra keys in object_data: {extra_keys}"
    assert template_keys == object_data_keys, "Object data keys do not match the template"


def test_story_object_completion(story_template):
    """Test that the object data keys match the template keys"""
    object_data = base_misp_builder.get_story_object_dict_empty()

    template_keys = set(story_template["attributes"].keys())
    object_data_keys = set(object_data.keys())

    missing_keys = template_keys - object_data_keys
    extra_keys = object_data_keys - template_keys

    assert len(missing_keys) == 0, f"Missing keys in object_data: {missing_keys}"
    assert len(extra_keys) == 0, f"Extra keys in object_data: {extra_keys}"
    assert template_keys == object_data_keys, "Object data keys do not match the template"


def test_story_utf8_decoding_mock(story_get_by_id_mock):
    """Test that the object data keys match the template keys"""

    core_api = CoreApi()
    surrogate_story = connector_tasks.get_story_by_id(core_api, ["11"])[0]
    print(f"{surrogate_story=}")
    assert surrogate_story["summary"] == "Following some utf 16 chars  and  and "
    assert surrogate_story["news_items"][0]["content"] == "Following some utf 16 chars "


def test_story_utf8_decoding(stories):
    """Test that the object data keys match the template keys"""
    story_json = json.dumps(stories)
    cleaned_json_str = connector_tasks.drop_utf16_surrogates(story_json)
    result = json.loads(cleaned_json_str)
    cleand_story = result[10]
    assert cleand_story["summary"] == "Following some utf 16 chars  and  and "


def test_drop_utf16_surrogates_edge_cases():
    """Test drop_utf16_surrogates for various edge cases."""

    # TODO: Fix commented edge cases
    # # 1. Inputs triggering a UnicodeDecodeError should return the original string.
    # # The invalid surrogate below might trigger a UnicodeDecodeError in some implementations.
    # input_invalid = 'Invalid surrogate: \udcff'
    # cleaned_invalid = connector_tasks.drop_utf16_surrogates(input_invalid)
    # assert cleaned_invalid == input_invalid, "Original string not returned on UnicodeDecodeError"

    # 2. Strings containing \n, \t, and " should be preserved.
    input_special = 'Line1\nLine2\t"Quoted text"'
    cleaned_special = connector_tasks.drop_utf16_surrogates(input_special)
    print(f"cleaned_special: {cleaned_special}")
    assert cleaned_special == input_special, 'Special characters (\\n, \\t, ") modified incorrectly'

    # 3. An empty string should be returned as an empty string.
    input_empty = ""
    cleaned_empty = connector_tasks.drop_utf16_surrogates(input_empty)
    print(f"cleaned_empty: {cleaned_empty}")
    assert cleaned_empty == "", "Empty string not handled correctly"

    # 4. A pure ASCII string remains unaltered.
    input_ascii = "This is a simple ASCII string."
    cleaned_ascii = connector_tasks.drop_utf16_surrogates(input_ascii)
    print(f"cleaned_ascii: {cleaned_ascii}")
    assert cleaned_ascii == input_ascii, "ASCII string altered unexpectedly"

    # # 5. Valid non-BMP characters (emojis) should not be modified.
    # input_emoji = 'I love 🍕 and 😄!'
    # cleaned_emoji = connector_tasks.drop_utf16_surrogates(input_emoji)
    # print(f"cleaned_emoji: {cleaned_emoji}")
    # assert cleaned_emoji == input_emoji, "Non-BMP characters altered unexpectedly"


def test_connector_story_processing(misp_connector_core_mock, misp_api_mock, caplog):
    import logging

    # Set the logging level to ERROR to capture only error logs and fail properly
    caplog.set_level(logging.ERROR, logger="root")

    result = connector_tasks.connector_task(
        connector_id="74981521-4ba7-4216-b9ca-ebc00ffec29c", story_ids=["ed13a0b1-4f5f-4c43-bdf2-820ee0d43448"]
    )
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert not errors, "Unexpected log errors:\n" + "\n".join(f"{r.levelname}: {r.message}" for r in errors)

    assert result is None


def test_valid_distribution():
    connector = MispConnector()
    connector.parse_parameters({"URL": "http://localhost", "API_KEY": "abc", "DISTRIBUTION": "2"})
    assert connector.distribution == 2


def test_empty_distribution_with_sharing_group():
    connector = MispConnector()
    connector.parse_parameters({"URL": "http://localhost", "API_KEY": "abc", "SHARING_GROUP_ID": "1", "DISTRIBUTION": ""})
    assert connector.distribution == 4


def test_empty_distribution_no_sharing_group():
    connector = MispConnector()
    connector.parse_parameters({"URL": "http://localhost", "API_KEY": "abc", "DISTRIBUTION": ""})
    assert connector.distribution == 0


def test_invalid_distribution_string():
    connector = MispConnector()
    connector.parse_parameters({"URL": "http://localhost", "API_KEY": "abc", "DISTRIBUTION": "abc"})
    assert connector.distribution == 0


def test_distribution_not_provided():
    connector = MispConnector()
    connector.parse_parameters({"URL": "http://localhost", "API_KEY": "abc", "SHARING_GROUP_ID": "1"})
    assert connector.distribution == 4
