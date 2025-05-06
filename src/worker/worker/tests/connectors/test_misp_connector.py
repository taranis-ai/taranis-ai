import json
import worker.connectors as connectors
from worker.connectors.connector_tasks import ConnectorTask


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


def test_story_utf8_decoding(stories):
    """Test that the object data keys match the template keys"""
    story_json = json.dumps(stories)
    cleaned_json_str = ConnectorTask().drop_utf16_surrogates(story_json)
    result = json.loads(cleaned_json_str)
    cleand_story = result[10]
    assert cleand_story["summary"] == "Following some utf 16 chars "
