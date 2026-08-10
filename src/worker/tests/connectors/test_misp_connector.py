import json
from types import SimpleNamespace

import pytest
from pymisp import exceptions

from worker.config import Config
from worker.connectors import base_misp_builder, connector_tasks
from worker.connectors.misp_connector import MispConnector
from worker.core_api import CoreApi


@pytest.fixture
def misp_connector_core_mock(requests_mock, stories):
    from tests.misp_connector_test_data import misp_connector

    requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/stories?story_id=ed13a0b1-4f5f-4c43-bdf2-820ee0d43448", json=[stories[11]])
    requests_mock.get(f"{Config.TARANIS_CORE_URL}/worker/connectors/74981521-4ba7-4216-b9ca-ebc00ffec29c", json=misp_connector)


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
        "74981521-4ba7-4216-b9ca-ebc00ffec29c",
        ["ed13a0b1-4f5f-4c43-bdf2-820ee0d43448"],
    )
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert not errors, "Unexpected log errors:\n" + "\n".join(f"{r.levelname}: {r.message}" for r in errors)
    assert result["connector_id"] == "74981521-4ba7-4216-b9ca-ebc00ffec29c"
    assert result["connector_type"] == "MISP_CONNECTOR"
    assert result["action"] == "synced"
    assert result["message"] == "Story synced to MISP"
    assert len(result["sync_results"]) == 1

    sync_result = result["sync_results"][0]
    assert sync_result["type"] == "misp_sync_story"
    assert sync_result["version"] == 1
    assert sync_result["story_id"] == "ed13a0b1-4f5f-4c43-bdf2-820ee0d43448"
    assert isinstance(sync_result["misp_event_uuid"], str) and sync_result["misp_event_uuid"]
    assert sync_result["news_item_ids_to_mark_external"] == ["06cc6fd0-a775-4923-bdef-8cd5381164ce"]


def test_connector_task_unknown_type_persists_failure(requests_mock, mock_job, monkeypatch):
    requests_mock.get(
        f"{Config.TARANIS_CORE_URL}/worker/connectors/connector-1",
        json={"id": "connector-1", "type": "unknown_connector"},
    )
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})
    monkeypatch.setattr(connector_tasks, "get_current_job", lambda: mock_job)

    with pytest.raises(RuntimeError, match="Failed to get connector with id: connector-1"):
        connector_tasks.connector_task("connector-1", ["story-1"])

    post_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
    assert len(post_calls) == 1
    assert post_calls[0].json() == {
        "id": "test-job-123",
        "task": "connector_task",
        "worker_id": "connector-1",
        "worker_type": "unknown_connector",
        "result": {
            "message": "Connector type 'unknown_connector' not implemented",
            "reason": "connector_not_implemented",
            "retryable": False,
            "data": {"connector_id": "connector-1", "story_ids": ["story-1"]},
        },
        "status": "FAILURE",
    }


def test_connector_task_story_load_failure_persists_failure(requests_mock, mock_job, monkeypatch):
    requests_mock.get(
        f"{Config.TARANIS_CORE_URL}/worker/connectors/connector-1",
        json={"id": "connector-1", "type": "misp_connector"},
    )
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/tasks", json={"message": "saved"})
    monkeypatch.setattr(connector_tasks, "get_current_job", lambda: mock_job)
    monkeypatch.setattr(connector_tasks, "_get_connector", lambda connector_type: object())

    def fail_load(*args, **kwargs):
        raise RuntimeError("Failed to get stories with id: ['story-1']")

    monkeypatch.setattr(connector_tasks, "_get_connector_data", fail_load)

    with pytest.raises(RuntimeError, match="Failed to get stories with id: \\['story-1'\\]"):
        connector_tasks.connector_task("connector-1", ["story-1"])

    post_calls = [req for req in requests_mock.request_history if req.method == "POST" and req.url.endswith("/tasks")]
    assert len(post_calls) == 1
    assert post_calls[0].json() == {
        "id": "test-job-123",
        "task": "connector_task",
        "worker_id": "connector-1",
        "worker_type": "misp_connector",
        "result": {
            "message": "Failed to get stories with id: ['story-1']",
            "reason": "connector_data_load_failed",
            "retryable": False,
            "data": {"connector_id": "connector-1", "story_ids": ["story-1"]},
        },
        "status": "FAILURE",
    }


def test_misp_sender_returns_sync_payload_after_successful_event(monkeypatch):
    from pymisp import MISPEvent

    connector = MispConnector()
    event = MISPEvent()
    event.uuid = "320d4589-cd71-4722-aa28-ea5530e99830"
    story = {
        "id": "story-123",
        "news_items": [
            {"id": "news-1", "last_change": "internal"},
            {"id": "news-2", "last_change": "external"},
        ],
    }

    monkeypatch.setattr(connector, "send_event_to_misp", lambda story_data, existing_uuid=None, auto_update=False: ("updated", event))

    assert connector.misp_sender(story, misp_event_uuid="existing-event-uuid") == {
        "action": "synced",
        "message": "Story synced to MISP",
        "sync_result": {
            "type": "misp_sync_story",
            "version": 1,
            "story_id": "story-123",
            "misp_event_uuid": "320d4589-cd71-4722-aa28-ea5530e99830",
            "news_item_ids_to_mark_external": ["news-1"],
        },
    }


def test_misp_sender_returns_proposal_result_for_proposals(monkeypatch):
    from pymisp import MISPShadowAttribute

    connector = MispConnector()

    monkeypatch.setattr(
        connector,
        "send_event_to_misp",
        lambda story_data, existing_uuid=None, auto_update=False: ("proposed", [MISPShadowAttribute()]),
    )

    assert connector.misp_sender({"id": "story-123", "news_items": [{"id": "news-1", "last_change": "internal"}]}, "existing-event-uuid") == {
        "action": "proposed",
        "message": "1 proposals submitted to MISP",
        "sync_result": None,
    }


def test_auto_update_blocked_result_includes_event_url(monkeypatch):
    connector = MispConnector()
    proposal_url = "https://misp.example/events/view/event-1"

    def blocked(*args, **kwargs):
        assert kwargs["auto_update"] is True
        return "blocked", proposal_url

    monkeypatch.setattr(connector, "send_event_to_misp", blocked)

    assert connector.misp_sender({"id": "story-123", "news_items": []}, "event-1", auto_update=True) == {
        "action": "blocked",
        "message": "MISP auto-update blocked by an external proposal",
        "sync_result": {"type": "misp_auto_update_blocked", "story_id": "story-123", "proposal_url": proposal_url},
    }


def test_blocked_results_are_counted_in_execution_summary():
    connector = MispConnector()

    assert connector._build_execution_result([])["action"] == "mixed"
    assert connector._build_execution_result(
        [{"action": "blocked", "message": "MISP auto-update blocked by an external proposal", "sync_result": {}}]
    ) == {
        "action": "blocked",
        "message": "MISP auto-update blocked by an external proposal",
        "sync_results": [],
    }
    assert (
        connector._build_execution_result(
            [
                {"action": "synced", "sync_result": {}},
                {"action": "blocked", "sync_result": {}},
                {"action": "failed", "sync_result": {}},
            ]
        )["message"]
        == "Processed 3 stories: 1 synced, 0 proposed, 1 blocked, 0 skipped, 1 failed"
    )


def test_pymisp_uses_configured_timeout(monkeypatch):
    connector = MispConnector()
    connector.url = "https://misp.example"
    connector.api_key = "key"
    connector.request_timeout = 42
    captured = {}

    monkeypatch.setattr("worker.connectors.misp_connector.PyMISP", lambda **kwargs: captured.update(kwargs) or object())
    monkeypatch.setattr(connector, "add_misp_event", lambda misp, story: None)

    connector.send_event_to_misp({})

    assert captured["timeout"] == 42


def test_auto_update_unowned_event_is_skipped(monkeypatch):
    connector = MispConnector()
    connector.org_id = "1"
    event = SimpleNamespace(to_dict=lambda: {"orgc_id": "2"})
    monkeypatch.setattr(connector, "get_event_by_uuid", lambda *args: event)

    assert connector.update_misp_event(SimpleNamespace(), {}, "event-1", auto_update=True) == ("skipped",)

    monkeypatch.setattr(connector, "send_event_to_misp", lambda *args, **kwargs: ("skipped",))
    result = connector.misp_sender({"id": "story-123", "news_items": []}, "event-1", auto_update=True)
    assert result == {"action": "skipped", "message": "MISP auto-update skipped for unowned event", "sync_result": None}
    assert connector._build_execution_result([result]) == {
        "action": "skipped",
        "message": "MISP auto-update skipped for unowned event",
        "sync_results": [],
    }


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        ([{"org_id": "2"}], True),
        ({"response": [{"org_id": "2"}]}, True),
        ({"ShadowAttribute": [{"org_id": "1"}]}, False),
        ({"response": {"ShadowAttribute": [{"org_id": "2"}]}}, True),
        ({}, False),
    ],
)
def test_external_proposal_response_shapes(response, expected):
    connector = MispConnector()
    connector.org_id = "1"
    misp = SimpleNamespace(_prepare_request=lambda *args: object(), _check_json_response=lambda _: response)

    assert connector.has_external_proposals(misp, "event-1") is expected


@pytest.mark.parametrize(
    ("failing_method", "error"),
    [
        ("_prepare_request", OSError("connection failed")),
        ("_check_json_response", exceptions.PyMISPUnexpectedResponse("invalid JSON")),
    ],
)
def test_auto_update_fails_closed_when_proposal_lookup_fails(monkeypatch, failing_method, error):
    connector = MispConnector()
    connector.org_id = "1"
    event = SimpleNamespace(to_dict=lambda: {"orgc_id": "1"})
    monkeypatch.setattr(connector, "get_event_by_uuid", lambda *args: event)
    misp = SimpleNamespace(_prepare_request=lambda *args: object(), _check_json_response=lambda *args: [])

    def fail(*args):
        raise error

    monkeypatch.setattr(misp, failing_method, fail)

    assert connector.update_misp_event(misp, {}, "event-1", auto_update=True) == ("failed",)


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
