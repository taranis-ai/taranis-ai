import json
import re
from unittest.mock import Mock

import pytest
import responses
from flask import Flask
from models.frontend_api import OPERATIONS

from frontend.config import Config
from frontend.router import base
from frontend.views.dashboard_views import DashboardView


@pytest.mark.parametrize("prefix", ["/", "/taranis/"])
def test_structured_frontend_routes_have_executable_contracts(prefix):
    app = Flask(__name__)
    app.config["APPLICATION_ROOT"] = prefix
    base.init(app)
    found = set()
    for rule in app.url_map.iter_rules():
        path = "/" + rule.rule.removeprefix(prefix)
        path = re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", path)
        view = app.view_functions[rule.endpoint]
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            operation = next((op for op in OPERATIONS if op.match(method, path) is not None), None)
            if operation is None:
                continue
            handler = getattr(getattr(view, "view_class", None), method.lower(), view)
            assert getattr(handler, "api_request_validated", False), (method, path)
            operation.parameters.model_json_schema()
            if operation.body:
                operation.body.json_schema()
            for response in operation.responses.values():
                response.body.json_schema()
            found.add((method, path))
    assert found == {(op.method, op.path) for op in OPERATIONS}


def test_conflict_payloads_validate_forms_and_cached_snapshots(app, authenticated_client, monkeypatch):
    incoming = {"id": "incoming", "title": "Incoming story", "news_items": []}
    snapshot = Mock(return_value=incoming)
    monkeypatch.setattr(DashboardView, "_load_incoming_story_snapshot", snapshot)
    monkeypatch.setattr(DashboardView, "news_item_conflict_view", Mock(return_value="Resolved"))
    payload = {"incoming_story_id": "incoming", "existing_story_ids": ["existing"], "incoming_news_item_ids": ["news"]}
    with responses.RequestsMock() as upstream:
        assert app.test_client().put("/conflicts/news-items", json=payload).status_code == 302
        snapshot.assert_not_called()
        upstream.put(
            f"{Config.TARANIS_CORE_URL}/connectors/conflicts/news-items",
            json={"message": "Resolved", "story_id": "incoming", "news_item_ids": ["news"]},
        )
        response = authenticated_client.put("/conflicts/news-items", json=payload)
        assert response.status_code == 200 and response.text == "Resolved"
        snapshot.assert_called_once_with("incoming")
        assert json.loads(upstream.calls[0].request.body)["incoming_story"] == incoming

        form = {"existing_story_ids[]": ["existing"], "incoming_news_item_ids[]": ["news"], "incoming_story": json.dumps(incoming)}
        response = authenticated_client.put("/conflicts/news-items", data=form)
        assert response.status_code == 200
        snapshot.assert_called_once_with("incoming")
        assert json.loads(upstream.calls[1].request.body)["incoming_story"] == incoming

        form["incoming_story"] = "{"
        response = authenticated_client.put("/conflicts/news-items", data=form)
        assert response.status_code == 400 and response.text == "Invalid request payload"
        snapshot.return_value = None
        response = authenticated_client.put("/conflicts/news-items", json=payload)
        assert response.status_code == 400 and response.text == "Invalid request payload"
        assert len(upstream.calls) == 2
