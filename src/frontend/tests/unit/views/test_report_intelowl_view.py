import json
from typing import Any

from flask import url_for

from frontend.config import Config


def test_report_selected_bot_action_posts_report_ids(authenticated_client_basic: Any, responses_mock: Any) -> None:
    responses_mock.post(
        f"{Config.TARANIS_CORE_URL}/analyze/report-items/botactions",
        json={"message": "Bot action queued"},
        status=200,
        content_type="application/json",
    )

    response = authenticated_client_basic.post(
        url_for("analyze.reports_trigger_bot"),
        data={"report_ids": ["report-1", "report-2"], "bot_id": "intel_owl_bot"},
    )

    body = responses_mock.calls[0].request.body
    assert response.status_code == 200
    assert "Bot action queued" in response.text
    assert json.loads(body.decode() if isinstance(body, bytes) else body) == {
        "report_ids": ["report-1", "report-2"],
        "bot_id": "intel_owl_bot",
    }
