#!/usr/bin/env python3
import uuid
import pytest
from flask import url_for

from playwright.sync_api import Page, expect
from playwright_helpers import PlaywrightHelpers


@pytest.mark.e2e_user
@pytest.mark.e2e_ci
@pytest.mark.usefixtures("e2e_ci")
class TestEndToEndUser(PlaywrightHelpers):
    """End-to-end tests for the Taranis AI user interface."""

    def test_login(self, taranis_frontend: Page):
        page = taranis_frontend
        self.add_keystroke_overlay(page)

        page.goto(url_for("base.login", _external=True))
        expect(page).to_have_title("Taranis AI", timeout=5000)

        self.highlight_element(page.get_by_placeholder("Username"))
        page.get_by_placeholder("Username").fill("user")
        self.highlight_element(page.get_by_placeholder("Password"))
        page.get_by_placeholder("Password").fill("test")
        page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")
        self.highlight_element(page.get_by_test_id("login-button")).click()
        expect(page.locator("#dashboard")).to_be_visible()

    def test_user_dashboard(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        page.goto(url_for("base.dashboard", _external=True))
        expect(page.locator("#dashboard")).to_be_visible()

    def test_user_assess(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        page.goto(url_for("assess.assess", _external=True))
        expect(page.get_by_test_id("assess")).to_be_visible()
        page.screenshot(path="./tests/playwright/screenshots/user_assess.png")

    def test_user_analyze(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        page.goto(url_for("analyze.analyze", _external=True))
        expect(page.get_by_test_id("analyze")).to_be_visible()
        page.screenshot(path="./tests/playwright/screenshots/user_analyze.png")

    def test_publish(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page
        product_title = f"test_product_{str(uuid.uuid4())[:8]}"

        def load_product_list():
            page.goto(url_for("publish.publish", _external=True))
            expect(page.get_by_test_id("product-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_products.png")

        def add_product():
            self.highlight_element(page.get_by_test_id("new-product-button")).click()
            expect(page.get_by_test_id("product-form")).to_be_visible()
            self.highlight_element(page.get_by_label("Product Type Select an item")).select_option("3")

            self.highlight_element(page.get_by_placeholder("Title")).fill(product_title)
            page.get_by_placeholder("Description").fill("This is a test product.")
            self.highlight_element(page.get_by_test_id("save-product")).click()

        load_product_list()
        add_product()
