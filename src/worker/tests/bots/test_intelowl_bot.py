from typing import Any

import pytest

import worker.bots as bots


pytestmark = pytest.mark.usefixtures("set_transformers_offline")


class FakeIntelOwlClient:
    def __init__(self) -> None:
        self.submissions: list[tuple[str, dict[str, Any]]] = []

    def send_observable_analysis_request(self, observable_name: str, **kwargs: Any) -> dict[str, Any]:
        self.submissions.append((observable_name, kwargs))
        return {"job_id": len(self.submissions), "status": "accepted"}

    def get_job_by_id(self, job_id: str) -> dict[str, Any]:
        assert len(self.submissions) == 2
        return {
            "id": job_id,
            "status": "reported_without_fails",
            "analyzer_reports": [{"name": "NVD_CVE", "status": "success", "report": {"score": 9.8}}],
        }


def test_intelowl_bot_submits_unique_tagged_observables_before_polling(monkeypatch: Any) -> None:
    stories = [
        {
            "id": "story-1",
            "news_items": [
                {
                    "id": "news-1",
                    "content": "1.2.3.4 is not an IOC until tagged",
                    "tags": [
                        {"name": "CVE-2024-1234", "tag_type": "cves"},
                        {"name": "analyst@example.com", "tag_type": "email"},
                    ],
                }
            ],
        },
        {"id": "story-2", "news_items": [{"id": "news-2", "tags": [{"name": "CVE-2024-1234", "tag_type": "cves"}]}]},
    ]
    client = FakeIntelOwlClient()
    bot = bots.IntelOwlBot()
    monkeypatch.setattr(bot.core_api, "get_stories", lambda filter_data: stories)
    monkeypatch.setattr(bot.core_api, "get_iocs", lambda iocs: {"items": []})
    monkeypatch.setattr(bot, "_create_client", lambda *args: client)
    bot.poll_delay_seconds = 0

    result = bot.execute(
        {
            "INTEL_OWL_URL": "https://intelowl.example",
            "INTEL_OWL_API_KEY": "secret-token",
            "filter": {"story_ids": ["story-1", "story-2"]},
        }
    )

    assert [call[0] for call in client.submissions] == ["CVE-2024-1234", "analyst@example.com"]
    assert client.submissions[0][1]["analyzers_requested"] == ["NVD_CVE", "Vulners"]
    assert client.submissions[1][1]["analyzers_requested"] == ["EmailRep", "HaveIBeenPwned"]
    assert result["enrichments"][0]["analyzers"][0]["report"] == {"score": 9.8}
