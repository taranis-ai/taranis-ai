from typing import Any

import pytest

import worker.bots as bots


pytestmark = pytest.mark.usefixtures("set_transformers_offline")


class FakeIntelOwlClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def send_observable_analysis_request(self, observable_name: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((observable_name, kwargs))
        return {"job_id": len(self.calls), "status": "accepted"}


def test_intelowl_bot_initializes() -> None:
    bots.IntelOwlBot()


def test_intelowl_bot_deduplicates_observables_and_skips_email(monkeypatch: Any) -> None:
    stories = [
        {
            "id": "story-1",
            "tags": {"CVE-2024-1234": {"name": "CVE-2024-1234", "tag_type": "cves"}},
            "news_items": [{"title": "", "review": "", "content": "CVE-2024-1234 1.2.3.4 analyst@example.com"}],
        },
        {
            "id": "story-2",
            "tags": [],
            "news_items": [{"title": "", "review": "", "content": "CVE-2024-1234 and 1.2.3.4"}],
        },
    ]
    client = FakeIntelOwlClient()
    bot = bots.IntelOwlBot()
    captured_filter: dict[str, Any] = {}

    def fake_get_stories(filter_dict: dict[str, Any]) -> list[dict[str, Any]]:
        captured_filter.update(filter_dict)
        return stories

    def fake_create_client(*args: Any) -> FakeIntelOwlClient:
        return client

    monkeypatch.setattr(bot.core_api, "get_stories", fake_get_stories)
    monkeypatch.setattr(bot, "_create_client", fake_create_client)

    result = bot.execute(
        {
            "INTEL_OWL_URL": "https://intelowl.example",
            "INTEL_OWL_API_KEY": "secret-token",
            "filter": {"story_ids": ["story-1", "story-2"]},
        }
    )

    submitted_names = [call[0] for call in client.calls]
    assert submitted_names.count("CVE-2024-1234") == 1
    assert submitted_names.count("1.2.3.4") == 1
    assert "analyst@example.com" not in submitted_names
    assert {"type": "email", "value": "analyst@example.com", "reason": "email_enrichment_disabled"} in result["skipped"]
    assert set(result["stories"]) == {"story-1", "story-2"}
    assert captured_filter == {"story_ids": ["story-1", "story-2"]}


def test_intelowl_bot_submits_email_when_enabled(monkeypatch: Any) -> None:
    client = FakeIntelOwlClient()
    bot = bots.IntelOwlBot()

    def fake_get_stories(filter_dict: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "id": "story-1",
                "tags": [],
                "news_items": [{"title": "", "review": "", "content": "Contact analyst@example.com about CVE-2024-1234"}],
            }
        ]

    def fake_create_client(*args: Any) -> FakeIntelOwlClient:
        return client

    monkeypatch.setattr(bot.core_api, "get_stories", fake_get_stories)
    monkeypatch.setattr(bot, "_create_client", fake_create_client)

    bot.execute(
        {
            "INTEL_OWL_URL": "https://intelowl.example",
            "INTEL_OWL_API_KEY": "secret-token",
            "INTEL_OWL_EMAIL_ENRICHMENT": "true",
            "filter": {"story_id": "story-1"},
        }
    )

    assert "analyst@example.com" in [call[0] for call in client.calls]


def test_intelowl_bot_returns_story_summary_without_observables(monkeypatch: Any) -> None:
    bot = bots.IntelOwlBot()

    def fake_get_stories(filter_dict: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"id": "story-1", "tags": [], "news_items": [{"title": "No indicators", "review": "", "content": "Nothing to enrich"}]}]

    def fail_create_client(*args: Any) -> None:
        raise AssertionError("IntelOwl client should not be created without observables")

    monkeypatch.setattr(bot.core_api, "get_stories", fake_get_stories)
    monkeypatch.setattr(bot, "_create_client", fail_create_client)

    result = bot.execute(
        {
            "INTEL_OWL_URL": "https://intelowl.example",
            "INTEL_OWL_API_KEY": "secret-token",
            "filter": {"story_id": "story-1"},
        }
    )

    assert result["message"] == "No IntelOwl observables found"
    assert result["stories"]["story-1"]["attribute"]["value"] == "IntelOwl enrichment: no submitted observables"


def test_intelowl_bot_analyzes_report_stories(monkeypatch: Any) -> None:
    client = FakeIntelOwlClient()
    bot = bots.IntelOwlBot()

    def fake_get_report_item(report_id: str) -> dict[str, Any]:
        return {"stories": [{"id": "story-1", "news_items": [{"content": "CVE-2024-1234"}]}]}

    def fake_create_client(*args: Any) -> FakeIntelOwlClient:
        return client

    monkeypatch.setattr(bot.core_api, "get_report_item", fake_get_report_item)
    monkeypatch.setattr(bot, "_create_client", fake_create_client)

    result = bot.execute(
        {
            "INTEL_OWL_URL": "https://intelowl.example",
            "INTEL_OWL_API_KEY": "secret-token",
            "filter": {"report_ids": ["report-1"]},
        }
    )

    assert [call[0] for call in client.calls] == ["CVE-2024-1234"]
    assert "CVE-2024-1234" in result["reports"]["report-1"]["value"]
