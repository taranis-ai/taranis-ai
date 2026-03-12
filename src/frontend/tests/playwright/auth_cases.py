from flask import url_for
from playwright.sync_api import Page, expect
from playwright_helpers import PlaywrightHelpers


def login(
    helpers: PlaywrightHelpers,
    page: Page,
    username: str,
    password: str,
) -> None:
    helpers.add_keystroke_overlay(page)

    page.goto(url_for("base.login", _external=True))
    expect(page).to_have_title("Taranis AI", timeout=5000)

    helpers.highlight_element(page.get_by_placeholder("Username"))
    expect(page.get_by_placeholder("Username")).to_have_attribute("required", "")
    page.get_by_placeholder("Username").fill(username)
    helpers.highlight_element(page.get_by_placeholder("Password"))
    expect(page.get_by_placeholder("Password")).to_have_attribute("required", "")
    page.get_by_placeholder("Password").fill(password)
    page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")
    helpers.highlight_element(page.get_by_test_id("login-button")).click()
    expect(page.locator("#dashboard")).to_be_visible()
