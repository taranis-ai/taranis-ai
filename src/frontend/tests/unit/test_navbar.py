from flask import render_template
from lxml import html


def test_navbar_hides_primary_labels_below_wide_breakpoint(app):
    with app.test_request_context("/"):
        markup = render_template("partials/navbar.html", is_admin=True)

    tree = html.fromstring(f"<div>{markup}</div>")
    nav = tree.xpath("//nav")[0]
    menu = tree.xpath("//ul[contains(concat(' ', normalize-space(@class), ' '), ' menu-horizontal ')]")[0]
    hidden_labels = tree.xpath("//nav/ul/li/a/span[contains(concat(' ', normalize-space(@class), ' '), ' 2xl:not-sr-only ')]")

    assert "shrink-0" in nav.get("class").split()
    assert "flex-nowrap" in menu.get("class").split()
    assert len(hidden_labels) == 6
    assert all("sr-only" in label.get("class").split() for label in hidden_labels)
