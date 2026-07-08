from typing import Any

import pytest

import worker.bots as bots


pytestmark = pytest.mark.usefixtures("set_transformers_offline")


class FakeIntelOwlClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.job_calls: list[str] = []

    def send_observable_analysis_request(self, observable_name: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((observable_name, kwargs))
        return {"job_id": len(self.calls), "status": "accepted"}

    def get_job_by_id(self, job_id: str) -> dict[str, Any]:
        self.job_calls.append(str(job_id))
        return {
            "id": job_id,
            "status": "reported_without_fails",
            "analyzer_reports": [{"name": "NIST_CVE_DB", "status": "success", "report": {"score": 9.8}}],
        }


def _patch_common(monkeypatch: Any, bot: bots.IntelOwlBot, client: FakeIntelOwlClient, stories: list[dict[str, Any]]) -> dict[str, Any]:
    captured_filter: dict[str, Any] = {}

    def fake_get_stories(filter_dict: dict[str, Any]) -> list[dict[str, Any]]:
        captured_filter.update(filter_dict)
        return stories

    monkeypatch.setattr(bot.core_api, "get_stories", fake_get_stories)
    monkeypatch.setattr(bot.core_api, "get_intelowl_enrichments", lambda iocs: {"items": []})
    monkeypatch.setattr(bot, "_create_client", lambda *args: client)
    bot.poll_delay_seconds = 0
    return captured_filter


def test_intelowl_bot_initializes() -> None:
    bots.IntelOwlBot()


def test_intelowl_bot_deduplicates_observable_tags_and_skips_email(monkeypatch: Any) -> None:
    stories = [
        {
            "id": "story-1",
            "news_items": [
                {
                    "id": "news-1",
                    "content": "1.2.3.4 should not be scraped from content",
                    "tags": [
                        {"name": "CVE-2024-1234", "tag_type": "cves"},
                        {"name": "analyst@example.com", "tag_type": "email_addresses"},
                    ],
                }
            ],
        },
        {"id": "story-2", "news_items": [{"id": "news-2", "tags": [{"name": "CVE-2024-1234", "tag_type": "cves"}]}]},
    ]
    client = FakeIntelOwlClient()
    bot = bots.IntelOwlBot()
    captured_filter = _patch_common(monkeypatch, bot, client, stories)

    result = bot.execute(
        {
            "INTEL_OWL_URL": "https://intelowl.example",
            "INTEL_OWL_API_KEY": "secret-token",
            "filter": {"story_ids": ["story-1", "story-2"]},
        }
    )

    submitted_names = [call[0] for call in client.calls]
    assert submitted_names == ["CVE-2024-1234"]
    assert "1.2.3.4" not in submitted_names
    assert {"type": "email", "value": "analyst@example.com", "reason": "email_enrichment_disabled"} in result["skipped"]
    assert result["enrichments"][0]["analyzers"][0]["report"] == {"score": 9.8}
    assert captured_filter == {"story_ids": ["story-1", "story-2"]}


def test_intelowl_bot_submits_email_when_enabled(monkeypatch: Any) -> None:
    stories = [{"id": "story-1", "news_items": [{"id": "news-1", "tags": [{"name": "analyst@example.com", "tag_type": "email"}]}]}]
    client = FakeIntelOwlClient()
    bot = bots.IntelOwlBot()
    _patch_common(monkeypatch, bot, client, stories)

    bot.execute(
        {
            "INTEL_OWL_URL": "https://intelowl.example",
            "INTEL_OWL_API_KEY": "secret-token",
            "INTEL_OWL_EMAIL_ENRICHMENT": "true",
            "filter": {"story_id": "story-1"},
        }
    )

    assert [call[0] for call in client.calls] == ["analyst@example.com"]


def test_intelowl_bot_returns_without_observables_when_no_ioc_tags(monkeypatch: Any) -> None:
    stories = [{"id": "story-1", "news_items": [{"id": "news-1", "content": "CVE-2024-1234", "tags": []}]}]
    client = FakeIntelOwlClient()
    bot = bots.IntelOwlBot()
    _patch_common(monkeypatch, bot, client, stories)

    result = bot.execute(
        {
            "INTEL_OWL_URL": "https://intelowl.example",
            "INTEL_OWL_API_KEY": "secret-token",
            "filter": {"story_id": "story-1"},
        }
    )

    assert result["message"] == "No IntelOwl observables found"
    assert client.calls == []


def test_intelowl_bot_refreshes_existing_pending_job(monkeypatch: Any) -> None:
    stories = [{"id": "story-1", "news_items": [{"id": "news-1", "tags": [{"name": "CVE-2024-1234", "tag_type": "cves"}]}]}]
    client = FakeIntelOwlClient()
    bot = bots.IntelOwlBot()
    _patch_common(monkeypatch, bot, client, stories)
    monkeypatch.setattr(
        bot.core_api,
        "get_intelowl_enrichments",
        lambda iocs: {"items": [{"ioc_type": "cve", "value": "CVE-2024-1234", "status": "running", "job_id": "42"}]},
    )

    result = bot.execute({"INTEL_OWL_URL": "https://intelowl.example", "INTEL_OWL_API_KEY": "secret-token"})

    assert client.calls == []
    assert client.job_calls == ["42"]
    assert result["enrichments"][0]["job_id"] == "42"
    assert result["enrichments"][0]["status"] == "reported_without_fails"


def test_intelowl_bot_rejects_report_filters() -> None:
    bot = bots.IntelOwlBot()

    with pytest.raises(ValueError, match="no longer supports report filters"):
        bot.execute(
            {
                "INTEL_OWL_URL": "https://intelowl.example",
                "INTEL_OWL_API_KEY": "secret-token",
                "filter": {"report_ids": ["report-1"]},
            }
        )
