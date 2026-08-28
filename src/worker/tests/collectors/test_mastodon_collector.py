import re
from typing import Any

import pytest
import requests

from worker.collectors.base_collector import NoChangeError
from worker.collectors.mastodon_collector import MastodonCollector, MastodonCollectorError
from worker.config import Config


INSTANCE_URL = "https://mastodon.example"


def source(
    timeline: str,
    *,
    max_entries: int = 42,
    hashtag: str = "security",
    account: str = "alice@example.social",
    access_token: str = "token",
    cursor: dict[str, str] | None = None,
) -> dict[str, Any]:
    parameters = {
        "INSTANCE_URL": INSTANCE_URL,
        "TIMELINE": timeline,
        "HASHTAG": hashtag,
        "ACCOUNT": account,
        "ACCESS_TOKEN": access_token,
        "USER_AGENT": "TaranisAI/Test",
        "PROXY_SERVER": "",
        "USE_GLOBAL_PROXY": False,
        "TLP_LEVEL": "clear",
        "REFRESH_INTERVAL": "",
    }
    result: dict[str, Any] = {"id": "source-1", "parameters": parameters, "collector_max_entries": max_entries}
    if cursor:
        result["mastodon_cursor"] = cursor
    return result


def status(
    status_id: int | str,
    *,
    content: str = "<p>Status content</p>",
    account_id: str = "account-1",
    account_name: str = "Alice",
    account_handle: str = "alice@example.social",
    spoiler_text: str = "",
    media_description: str | None = None,
    reblog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    media_attachments = [] if media_description is None else [{"description": media_description}]
    return {
        "id": str(status_id),
        "created_at": "2026-08-27T10:00:00.000Z",
        "content": content,
        "spoiler_text": spoiler_text,
        "language": "en",
        "url": f"{INSTANCE_URL}/@{account_handle.split('@')[0]}/{status_id}",
        "uri": f"{INSTANCE_URL}/users/{account_handle.split('@')[0]}/statuses/{status_id}",
        "account": {
            "id": account_id,
            "display_name": account_name,
            "acct": account_handle,
            "url": f"{INSTANCE_URL}/@{account_handle.split('@')[0]}",
        },
        "media_attachments": media_attachments,
        "reblog": reblog,
    }


def _published_items(requests_mock) -> list[dict]:
    request = next(request for request in requests_mock.request_history if request.url == f"{Config.TARANIS_CORE_URL}/worker/news-items")
    return request.json()


def test_hashtag_collection_maps_boost_and_media_and_advances_cursor(requests_mock):
    original = status(
        88,
        content="<p>Boosted <b>post</b></p>",
        spoiler_text="<strong>Content warning</strong>",
        account_name="Bob",
        account_handle="bob@example.social",
    )
    responses = [status("opaque-b", reblog=original), status("opaque-a", content="", media_description="Network diagram")]

    def hashtag_response(request, _context):
        return [] if "max_id" in request.qs else responses

    requests_mock.get(re.compile(rf"{INSTANCE_URL}/api/v1/timelines/tag/security.*"), json=hashtag_response)
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/worker/news-items", json={"message": "Added 2 items"})

    collector = MastodonCollector()
    assert collector.collect(source("hashtag", max_entries=2, access_token="")) == "Added 2 items"

    items = _published_items(requests_mock)
    assert items[0]["author"] == "Bob"
    assert items[0]["title"] == "Content warning"
    assert items[0]["content"] == "Boosted post"
    assert items[0]["link"].endswith("/88")
    assert items[1]["content"] == "Network diagram"
    assert collector.mastodon_cursor == {
        "timeline": f"{INSTANCE_URL}|hashtag|security",
        "last_status_id": "opaque-b",
    }


def test_home_collection_uses_local_cursor_without_gaps(requests_mock):
    requests_mock.get(f"{INSTANCE_URL}/api/v1/accounts/verify_credentials", json={"id": "account-1"})

    def home_response(request, _context):
        if request.qs.get("min_id") == ["100"]:
            return [status(status_id) for status_id in range(140, 100, -1)]
        if request.qs.get("min_id") == ["140"]:
            return [status(142), status(141)]
        return []

    requests_mock.get(re.compile(rf"{INSTANCE_URL}/api/v1/timelines/home.*"), json=home_response)
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/worker/news-items", json={"message": "Added"})
    cursor = {"timeline": f"{INSTANCE_URL}|home|account-1", "last_status_id": "100"}

    collector = MastodonCollector()
    collector.collect(source("home", max_entries=42, cursor=cursor))

    assert len(_published_items(requests_mock)) == 42
    assert collector.mastodon_cursor == {"timeline": f"{INSTANCE_URL}|home|account-1", "last_status_id": "142"}
    home_requests = [request for request in requests_mock.request_history if "/api/v1/timelines/home" in request.url]
    assert [request.qs["min_id"][0] for request in home_requests] == ["100", "140"]
    assert all(request.headers["Authorization"] == "Bearer token" for request in home_requests)


def test_account_collection_resolves_configured_account(requests_mock):
    requests_mock.get(f"{INSTANCE_URL}/api/v1/accounts/lookup", json={"id": "account-9"})
    requests_mock.get(re.compile(rf"{INSTANCE_URL}/api/v1/accounts/account-9/statuses.*"), json=[])

    collector = MastodonCollector()
    with pytest.raises(NoChangeError, match="No new Mastodon statuses"):
        collector.collect(source("account"))

    lookup = next(request for request in requests_mock.request_history if "/api/v1/accounts/lookup" in request.url)
    assert lookup.qs["acct"] == ["alice@example.social"]


def test_bootstrap_honors_shared_collector_entry_limit(requests_mock):
    first_page = [status(status_id) for status_id in range(100, 60, -1)]
    second_page = [status(60), status(59)]

    def hashtag_response(request, _context):
        return second_page if request.qs.get("max_id") == ["61"] else first_page

    requests_mock.get(re.compile(rf"{INSTANCE_URL}/api/v1/timelines/tag/security.*"), json=hashtag_response)
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/worker/news-items", json={"message": "Added"})

    collector = MastodonCollector()
    collector.collect(source("hashtag", max_entries=42, access_token=""))

    assert len(_published_items(requests_mock)) == 42
    assert collector.mastodon_cursor["last_status_id"] == "100"


def test_preview_ignores_and_preserves_cursor(requests_mock):
    requests_mock.get(re.compile(rf"{INSTANCE_URL}/api/v1/timelines/tag/security.*"), json=[status(200)])
    cursor = {"timeline": f"{INSTANCE_URL}|hashtag|security", "last_status_id": "100"}

    collector = MastodonCollector()
    preview = collector.preview_collector(source("hashtag", max_entries=1, access_token="", cursor=cursor))

    request = next(request for request in requests_mock.request_history if "/api/v1/timelines/tag/security" in request.url)
    assert "min_id" not in request.qs
    assert collector.mastodon_cursor == cursor
    assert preview[0]["link"].endswith("/200")


def test_changed_timeline_identity_bootstraps_and_replaces_cursor(requests_mock):
    requests_mock.get(re.compile(rf"{INSTANCE_URL}/api/v1/timelines/tag/security.*"), json=[status(200)])
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/worker/news-items", json={"message": "Added"})
    cursor = {"timeline": f"{INSTANCE_URL}|hashtag|old-target", "last_status_id": "100"}

    collector = MastodonCollector()
    collector.collect(source("hashtag", max_entries=1, access_token="", cursor=cursor))

    request = next(request for request in requests_mock.request_history if "/api/v1/timelines/tag/security" in request.url)
    assert "min_id" not in request.qs
    assert collector.mastodon_cursor == {
        "timeline": f"{INSTANCE_URL}|hashtag|security",
        "last_status_id": "200",
    }


def test_duplicate_only_publication_advances_cursor(requests_mock):
    requests_mock.get(re.compile(rf"{INSTANCE_URL}/api/v1/timelines/tag/security.*"), json=[status(101)])
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/worker/news-items", json={"message": "All news items were skipped"})
    cursor = {"timeline": f"{INSTANCE_URL}|hashtag|security", "last_status_id": "100"}

    collector = MastodonCollector()
    with pytest.raises(NoChangeError, match="All news items were skipped"):
        collector.collect(source("hashtag", max_entries=1, access_token="", cursor=cursor))

    assert collector.mastodon_cursor["last_status_id"] == "101"


def test_core_publication_failure_preserves_cursor(requests_mock):
    requests_mock.get(re.compile(rf"{INSTANCE_URL}/api/v1/timelines/tag/security.*"), json=[status(101)])
    requests_mock.post(f"{Config.TARANIS_CORE_URL}/worker/news-items", status_code=503, json={"error": "internal details"})
    cursor = {"timeline": f"{INSTANCE_URL}|hashtag|security", "last_status_id": "100"}

    collector = MastodonCollector()
    with pytest.raises(MastodonCollectorError) as exception:
        collector.collect(source("hashtag", max_entries=1, access_token="", cursor=cursor))

    assert exception.value.public_message == "Collected Mastodon statuses could not be published"
    assert exception.value.reason == "mastodon_publish_failed"
    assert collector.mastodon_cursor == cursor


@pytest.mark.parametrize(
    ("status_code", "access_token", "public_message", "reason"),
    [
        (401, "secret-token-value", "Mastodon authentication failed or access was denied", "mastodon_authentication_failed"),
        (404, "secret-token-value", "The configured Mastodon timeline or account was not found", "mastodon_not_found"),
        (429, "secret-token-value", "Mastodon rate limit exceeded; increase the refresh interval", "mastodon_rate_limited"),
        (500, "secret-token-value", "The Mastodon instance rejected the collection request", "mastodon_api_error"),
        (422, "", "This Mastodon instance requires an access token to collect hashtags", "mastodon_access_token_required"),
    ],
)
def test_api_errors_are_replaced_with_curated_messages(requests_mock, status_code, access_token, public_message, reason):
    requests_mock.get(
        re.compile(rf"{INSTANCE_URL}/api/v1/timelines/tag/security.*"),
        status_code=status_code,
        json={"error": "token secret-token-value was rejected"},
    )

    collector = MastodonCollector()
    with pytest.raises(MastodonCollectorError) as exception:
        collector.collect(source("hashtag", access_token=access_token))

    assert exception.value.public_message == public_message
    assert exception.value.reason == reason
    assert "secret-token-value" not in exception.value.public_message


def test_network_errors_are_replaced_with_a_curated_message(requests_mock):
    requests_mock.get(
        re.compile(rf"{INSTANCE_URL}/api/v1/timelines/tag/security.*"),
        exc=requests.exceptions.ConnectTimeout("sensitive network details"),
    )

    collector = MastodonCollector()
    with pytest.raises(MastodonCollectorError) as exception:
        collector.collect(source("hashtag", access_token=""))

    assert exception.value.public_message == "The Mastodon instance could not be reached"
    assert exception.value.reason == "mastodon_unavailable"
