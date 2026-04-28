#!/usr/bin/env python3

import pytest
from flask import url_for
from playwright.sync_api import Browser, BrowserContext, Page, expect
from playwright_helpers import PlaywrightHelpers


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
        context, page = self._open_login_page(browser, {"width": 1440, "height": 900})

        try:
            banner = page.locator("#viewport-notification")

            expect(banner).to_be_hidden()

            page.set_viewport_size({"width": 1439, "height": 900})
            expect(banner).to_be_visible()
            expect(banner).to_contain_text("below WXGA+")

            page.set_viewport_size({"width": 1440, "height": 599})
            expect(banner).to_be_visible()

            page.set_viewport_size({"width": 1440, "height": 900})
            expect(banner).to_be_hidden()
        finally:
            page.close()
            context.close()
