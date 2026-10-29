from flask import render_template, url_for
from lxml import html

from frontend.cache import add_user_to_cache


def test_tactical_preview_scenarios_and_host_inspection(authenticated_client_basic, auth_user_basic, responses_mock):
    asset_reader = auth_user_basic.model_copy(deep=True)
    asset_reader.permissions = ["ASSETS_ACCESS"]
    add_user_to_cache(asset_reader.model_dump(mode="json"))
    endpoint = url_for("assets.tactical")

    response = authenticated_client_basic.get(endpoint)
    assert response.status_code == 200
    tree = html.fromstring(response.text)
    assert tree.xpath('//*[@data-test-id="tactical-preview"]/@data-scenario') == ["database"]
    assert tree.xpath('//*[@data-test-id="tactical-inspector"]/@data-host-id') == ["db-01"]
    assert tree.xpath('//*[@data-test-id="tactical-impact-count"]')[0].text_content().strip() == "4"
    assert tree.xpath("//nav//a[@href=$endpoint]", endpoint=endpoint)

    portal_link = tree.xpath('//*[@data-test-id="tactical-host"][@data-host-id="portal-01"]')[0]
    inspected = authenticated_client_basic.get(portal_link.get("href"))
    assert inspected.status_code == 200
    tree = html.fromstring(inspected.text)
    assert tree.xpath('//*[@data-test-id="tactical-preview"]/@data-scenario') == ["database"]
    assert tree.xpath('//*[@data-test-id="tactical-inspector"]/@data-host-id') == ["portal-01"]

    for scenario, root, potential in (("queue", "broker-01", "2"), ("staging", "staging-01", "0")):
        changed = authenticated_client_basic.get(endpoint, query_string={"scenario": scenario})
        assert changed.status_code == 200
        tree = html.fromstring(changed.text)
        assert tree.xpath('//*[@data-test-id="tactical-preview"]/@data-scenario') == [scenario]
        assert tree.xpath('//*[@data-test-id="tactical-inspector"]/@data-host-id') == [root]
        assert tree.xpath('//*[@data-test-id="tactical-impact-count"]')[0].text_content().strip() == potential

    fallback = authenticated_client_basic.get(endpoint, query_string={"scenario": "missing", "host": "missing"})
    assert fallback.status_code == 200
    tree = html.fromstring(fallback.text)
    assert tree.xpath('//*[@data-test-id="tactical-preview"]/@data-scenario') == ["database"]
    assert tree.xpath('//*[@data-test-id="tactical-inspector"]/@data-host-id') == ["db-01"]
    assert not responses_mock.calls


def test_tactical_preview_requires_asset_access(app, authenticated_client_basic, auth_user_basic, responses_mock):
    reader = auth_user_basic.model_copy(deep=True)
    reader.permissions = ["ASSESS_ACCESS"]
    add_user_to_cache(reader.model_dump(mode="json"))
    endpoint = url_for("assets.tactical")

    assert authenticated_client_basic.get(endpoint).status_code == 403
    with app.test_request_context("/"):
        navbar = render_template("partials/navbar.html", is_admin=False, current_user=reader, chat_enabled=False)
    assert not html.fromstring(f"<div>{navbar}</div>").xpath("//nav//a[@href=$endpoint]", endpoint=endpoint)
    assert not responses_mock.calls
