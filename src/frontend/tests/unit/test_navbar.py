from unittest.mock import Mock

import pytest
from flask import render_template, url_for
from lxml import html
from models.dashboard import CoreStatus
from requests import ConnectionError

from frontend.cache import cache
from frontend.config import Config
from frontend.data_persistence import DataPersistenceLayer


def test_navbar_hides_primary_labels_below_wide_breakpoint(app, auth_user):
    with app.test_request_context("/"):
        markup = render_template("partials/navbar.html", is_admin=True, current_user=auth_user, chat_enabled=False)

    tree = html.fromstring(f"<div>{markup}</div>")
    nav = tree.xpath("//nav")[0]
    menu = tree.xpath("//ul[contains(concat(' ', normalize-space(@class), ' '), ' menu-horizontal ')]")[0]
    hidden_labels = tree.xpath("//nav/ul/li/a/span[contains(concat(' ', normalize-space(@class), ' '), ' 2xl:not-sr-only ')]")

    assert "shrink-0" in nav.get("class").split()
    assert "flex-nowrap" in menu.get("class").split()
    assert len(hidden_labels) == 6
    assert all("sr-only" in label.get("class").split() for label in hidden_labels)


@pytest.mark.parametrize("client_fixture", ["authenticated_client", "authenticated_client_basic"])
@pytest.mark.parametrize(
    ("frontend_debug", "core_status", "visible"),
    [
        (False, {"isalive": True, "debug": False}, False),
        (False, {"isalive": True, "debug": True}, True),
        (True, {"isalive": True, "debug": False}, True),
        (True, {"isalive": True, "debug": True}, True),
        (False, {"isalive": True}, False),
    ],
)
def test_navbar_debug_badge(app, request, monkeypatch, responses, client_fixture, frontend_debug, core_status, visible):
    client = request.getfixturevalue(client_fixture)
    monkeypatch.setitem(app.config, "DEBUG", frontend_debug)
    if not frontend_debug:
        responses.get(f"{Config.TARANIS_CORE_URL}/isalive", json=core_status)

    with app.app_context():
        url = url_for("user.settings")
    response = client.get(url)

    assert response.status_code == 200
    badges = html.fromstring(response.text).xpath('//*[@data-test-id="debug-mode-badge"]')
    assert len(badges) == int(visible)
    if badges:
        assert badges[0].text == "Debug mode"
    assert len(responses.calls) == int(not frontend_debug)


@pytest.mark.parametrize(
    "core_response",
    [
        {"status": 503},
        {"body": ConnectionError("private connection details")},
        {"json": {"isalive": True, "debug": "invalid"}},
        {"status": 403, "json": {"error": "private connection details"}},
    ],
)
def test_navbar_debug_status_failure_keeps_page_usable(app, authenticated_client_basic, monkeypatch, responses, caplog, core_response):
    monkeypatch.setitem(app.config, "DEBUG", False)
    responses.get(f"{Config.TARANIS_CORE_URL}/isalive", **core_response)

    with app.app_context():
        url = url_for("user.settings")
    response = authenticated_client_basic.get(url)

    assert response.status_code == 200
    assert 'id="user-settings-page"' in response.text
    assert "debug-mode-badge" not in response.text
    assert "private connection details" not in response.text
    assert caplog.records


def test_navbar_caches_core_debug_status(app, auth_user_basic, monkeypatch, responses, test_cache_backend):
    monkeypatch.setitem(app.config, "DEBUG", False)
    cache_set = Mock(wraps=cache.set)
    monkeypatch.setattr(cache, "set", cache_set)
    responses.get(f"{Config.TARANIS_CORE_URL}/isalive", json={"isalive": True, "debug": True})
    responses.get(f"{Config.TARANIS_CORE_URL}/isalive", json={"isalive": True, "debug": False})

    with app.test_request_context("/"):
        first = render_template("partials/navbar.html", current_user=auth_user_basic)
        cached = render_template("partials/navbar.html", current_user=auth_user_basic)
        assert len(responses.calls) == 1
        assert cache_set.call_args.kwargs["timeout"] == 5

        cache.delete(DataPersistenceLayer().make_detail_cache_key(CoreStatus))
        refreshed = render_template("partials/navbar.html", current_user=auth_user_basic)

    assert first.count('data-test-id="debug-mode-badge"') == 1
    assert cached.count('data-test-id="debug-mode-badge"') == 1
    assert "debug-mode-badge" not in refreshed
    assert len(responses.calls) == 2


def test_debug_status_lookup_only_runs_for_full_page_navbar(app, authenticated_client_basic, monkeypatch, responses):
    monkeypatch.setitem(app.config, "DEBUG", False)
    responses.get(f"{Config.TARANIS_CORE_URL}/auth/method", json={"auth_method": "database"})
    responses.get(f"{Config.TARANIS_CORE_URL}/tasks/user", json={"items": [], "total_count": 0})

    with app.app_context():
        login_url = url_for("base.login")
        tasks_url = url_for("user.tasks")
        login = authenticated_client_basic.get(login_url)
    fragment = authenticated_client_basic.get(tasks_url, headers={"HX-Request": "true"})

    assert login.status_code == fragment.status_code == 200
    assert "debug-mode-badge" not in login.text
    assert "debug-mode-badge" not in fragment.text
    assert all(not call.request.url.endswith("/isalive") for call in responses.calls)

    responses.get(f"{Config.TARANIS_CORE_URL}/isalive", json={"isalive": True, "debug": True})
    restored = authenticated_client_basic.get(tasks_url, headers={"HX-Request": "true", "HX-History-Restore-Request": "true"})

    assert restored.status_code == 200
    assert restored.text.count('data-test-id="debug-mode-badge"') == 1
