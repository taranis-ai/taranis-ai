import json
import worker.connectors as connectors
from worker.connectors import connector_tasks


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
    """Test that the object data keys match the template keys"""

    connector = connector_tasks.ConnectorTask()
    surrogate_story = connector.get_story_by_id(["11"])[0]
    print(f"{surrogate_story=}")
    assert surrogate_story["summary"] == "Following some utf 16 chars  and  and "
    assert surrogate_story["news_items"][0]["content"] == "Following some utf 16 chars "


def test_story_utf8_decoding(stories):
    """Test that the object data keys match the template keys"""
    story_json = json.dumps(stories)
    cleaned_json_str = connector_tasks.ConnectorTask().drop_utf16_surrogates(story_json)
    result = json.loads(cleaned_json_str)
    cleand_story = result[10]
    assert cleand_story["summary"] == "Following some utf 16 chars  and  and "


def test_drop_utf16_surrogates_edge_cases():
    """Test drop_utf16_surrogates for various edge cases."""
    task = connector_tasks.ConnectorTask()

    # TODO: Fix commented edge cases
    # # 1. Inputs triggering a UnicodeDecodeError should return the original string.
    # # The invalid surrogate below might trigger a UnicodeDecodeError in some implementations.
    # input_invalid = 'Invalid surrogate: \udcff'
    # cleaned_invalid = task.drop_utf16_surrogates(input_invalid)
    # assert cleaned_invalid == input_invalid, "Original string not returned on UnicodeDecodeError"

    # 2. Strings containing \n, \t, and " should be preserved.
    input_special = 'Line1\nLine2\t"Quoted text"'
    cleaned_special = task.drop_utf16_surrogates(input_special)
    print(f"cleaned_special: {cleaned_special}")
    assert cleaned_special == input_special, 'Special characters (\\n, \\t, ") modified incorrectly'

    # 3. An empty string should be returned as an empty string.
    input_empty = ""
    cleaned_empty = task.drop_utf16_surrogates(input_empty)
    print(f"cleaned_empty: {cleaned_empty}")
    assert cleaned_empty == "", "Empty string not handled correctly"

    # 4. A pure ASCII string remains unaltered.
    input_ascii = "This is a simple ASCII string."
    cleaned_ascii = task.drop_utf16_surrogates(input_ascii)
    print(f"cleaned_ascii: {cleaned_ascii}")
    assert cleaned_ascii == input_ascii, "ASCII string altered unexpectedly"

    # # 5. Valid non-BMP characters (emojis) should not be modified.
    # input_emoji = 'I love 🍕 and 😄!'
    # cleaned_emoji = task.drop_utf16_surrogates(input_emoji)
    # print(f"cleaned_emoji: {cleaned_emoji}")
    # assert cleaned_emoji == input_emoji, "Non-BMP characters altered unexpectedly"
