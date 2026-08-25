from pathlib import Path

import pytest
from playwright.sync_api import Page


pytestmark = pytest.mark.e2e_ci

NOTIFICATION_CENTER_JS_PATH = Path(__file__).parents[2] / "frontend/static/js/notification-center.js"


def test_notification_storage_only_records_explicit_events(page: Page):
    page.add_init_script(path=str(NOTIFICATION_CENTER_JS_PATH))
    page.route("https://example.test/", lambda route: route.fulfill(body='<div class="alert">Not a notification</div>'))
    page.goto("https://example.test/")

    assert page.evaluate("() => taranisNotifications.read()") == []

    page.evaluate("() => taranisNotifications.add({ message: '  Saved  ', level: 'success' })")
    notification = page.evaluate("() => taranisNotifications.read()[0]")

    assert notification["message"] == "Saved"
    assert notification["level"] == "success"

    page.evaluate("() => { for (let index = 0; index < 101; index++) taranisNotifications.add({ message: String(index) }) }")

    assert page.evaluate("() => taranisNotifications.read().length") == 100
    assert page.evaluate("() => taranisNotifications.read()[0].message") == "100"

    page.evaluate("() => taranisNotifications.clear()")

    assert page.evaluate("() => taranisNotifications.read()") == []
