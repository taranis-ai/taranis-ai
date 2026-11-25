from flask import url_for
from lxml import html
from models.llm import OPENROUTER_DECISIONS_URL
from responses import matchers

from frontend.config import Config


def test_decisions_model_suggestions_use_provider_url(app, authenticated_client, responses_mock):
    endpoint = responses_mock.get(
        f"{Config.TARANIS_CORE_URL}/settings/llm-model-suggestions",
        match=[matchers.query_param_matcher({"systemone": OPENROUTER_DECISIONS_URL}, strict_match=False)],
        json={"systemone": [{"id": "test/decisions", "name": "Decisions model"}]},
    )
    with app.test_request_context():
        response = authenticated_client.get(
            url_for("admin_settings.settings_action", action="llm-model-suggestions"),
            query_string={"base_url": f"{OPENROUTER_DECISIONS_URL}/", "decisions[api_format]": "systemone", "decisions[base_url]": ""},
        )

    assert response.status_code == 200
    assert endpoint.call_count == 1
    assert html.fromstring(response.data).xpath('//datalist[@id="llm--decisions-models"]/option/@value') == ["test/decisions"]
