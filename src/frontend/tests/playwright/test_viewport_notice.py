#!/usr/bin/env python3

import pytest
from flask import url_for
from playwright.sync_api import Browser, BrowserContext, Page, expect
from playwright_helpers import PlaywrightHelpers


VIEWPORT_WARNING_STORAGE_KEY = "taranis.viewportWarningDismissed"


@pytest.mark.e2e_user
@pytest.mark.e2e_ci
@pytest.mark.usefixtures("e2e_ci")
class TestViewportNotice(PlaywrightHelpers):
    def _open_login_page(self, browser: Browser, viewport: dict[str, int]) -> tuple[BrowserContext, Page]:
        context = browser.new_context(viewport=viewport)
        page = context.new_page()
        page.goto(url_for("base.login", _external=True))
        return context, page

    def test_warning_bar_tracks_wxga_plus_threshold(self, browser: Browser, e2e_server):
        context, page = self._open_login_page(browser, {"width": 1440, "height": 600})

        try:
            banner = page.locator("#viewport-notification")

            expect(banner).to_be_hidden()

            page.set_viewport_size({"width": 1440, "height": 599})
            expect(banner).to_be_visible()
            expect(banner).to_contain_text("Resolutions below WXGA+ are not supported")

            page.get_by_test_id("viewport-notification-dismiss").click()
            expect(banner).to_be_hidden()
            assert page.evaluate(f"localStorage.getItem('{VIEWPORT_WARNING_STORAGE_KEY}')") == "true"

            page.get_by_placeholder("Username").fill("admin")
            page.get_by_placeholder("Password").fill("admin")
            page.get_by_test_id("login-button").click()
            expect(page.locator("#dashboard")).to_be_visible()
            expect(banner).to_be_hidden()
            assert page.evaluate(f"localStorage.getItem('{VIEWPORT_WARNING_STORAGE_KEY}')") == "true"

            page.reload()
            expect(page.locator("#dashboard")).to_be_visible()
            expect(banner).to_be_hidden()

            page.get_by_test_id("user-menu-button").click()
            expect(page.get_by_test_id("logout-link")).to_be_visible()
            page.get_by_test_id("logout-link").click()
            expect(page.get_by_test_id("login-form")).to_be_visible()
            expect(banner).to_be_visible()
            assert page.evaluate(f"localStorage.getItem('{VIEWPORT_WARNING_STORAGE_KEY}')") is None

            page.set_viewport_size({"width": 1440, "height": 599})
            expect(banner).to_be_visible()
        finally:
            page.close()
            context.close()
