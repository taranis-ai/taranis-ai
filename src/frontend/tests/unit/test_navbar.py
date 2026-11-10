import pytest
from flask import render_template, url_for
from lxml import html

from frontend.config import Config


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
def test_debug_badge_is_absent_outside_admin_dashboard(app, request, monkeypatch, responses, client_fixture):
    """Keep settings, content fragments, and login free of debug status requests."""
    client = request.getfixturevalue(client_fixture)
    monkeypatch.setattr(Config, "DEBUG", True)
    responses.get(f"{Config.TARANIS_CORE_URL}/auth/method", json={"auth_method": "database"})

    with app.app_context():
        settings_url = url_for("user.settings")
        fragment_url = url_for("base.notification")
        login_url = url_for("base.login")

    for response in (
        client.get(settings_url),
        client.get(fragment_url, headers={"HX-Request": "true"}),
        client.get(login_url),
    ):
        assert response.status_code == 200
        assert "debug-mode-badge" not in response.text

    assert [call.request.url for call in responses.calls] == [f"{Config.TARANIS_CORE_URL}/auth/method"]
