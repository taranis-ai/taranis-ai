import worker.connectors as connectors


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


def test_story_utf8_decoding(story_get_by_id_mock):
    """Test that the object data keys match the template keys"""
    from worker.connectors import connector_tasks

    connector = connector_tasks.ConnectorTask()
    surrogate_story = connector.get_story_by_id(["11"])[0]
    print(f"{surrogate_story=}")
    assert surrogate_story["summary"] == "Following some utf 16 chars "
    assert surrogate_story["news_items"][0]["content"] == "Following some utf 16 chars "
