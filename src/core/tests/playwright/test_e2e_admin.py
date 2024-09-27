#!/usr/bin/env python3
import re
import time

from playwright.sync_api import Page, expect
import pytest

from playwright_helpers import PlaywrightHelpers


@pytest.mark.e2e_admin
class TestEndToEndAdmin(PlaywrightHelpers):
    """End-to-end tests for the Taranis AI admin interface."""

    wait_duration: float = 0
    ci_run: bool = True

    def test_setup_pwhelpers(self, taranis_frontend: Page):
        PlaywrightHelpers.config_pwhelpers(self, wait_duration=self.wait_duration, ci_run=self.ci_run)

    def test_login(self, taranis_frontend: Page):
        page = taranis_frontend
        self.add_keystroke_overlay(page)

        expect(page).to_have_title("Taranis AI", timeout=5000)

        self.highlight_element(page.get_by_placeholder("Username"))
        page.get_by_placeholder("Username").fill("admin")
        self.highlight_element(page.get_by_placeholder("Password"))
        page.get_by_placeholder("Password").fill("admin")
        page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")
        self.highlight_element(page.locator("role=button")).click()

    def test_enable_infinite_scroll(self, taranis_frontend: Page):
        page = taranis_frontend
        page.get_by_role("button").nth(1).click()
        page.get_by_text("Settings").click()
        page.get_by_label("Infinite Scroll").check()
        page.get_by_role("button", name="Save").click()
        expect(page.get_by_text("Profile updated")).to_be_visible()


    def test_admin_user_management(self, taranis_frontend: Page):
        page = taranis_frontend

        def add_organization():
            page.get_by_role("link", name="Administration").click()
            page.get_by_role("link", name="Organizations").click()
            page.get_by_role("button", name="New Item").click()
            page.get_by_label("Name").click()
            page.get_by_label("Name").fill("Test organizations")
            page.get_by_label("Description").fill("Test description of an organization")
            page.get_by_label("Street").fill("Test Street")
            page.get_by_label("City").fill("Test City")
            page.get_by_label("Zip").fill("9999")
            page.get_by_label("Country").fill("Test Country")
            time.sleep(0.3)
            page.screenshot(path="./tests/playwright/screenshots/docs_organization_add.png")
            page.get_by_role("button", name="Submit").click()
            expect(page.get_by_text("Successfully created Test")).to_be_visible()
            page.locator("div").filter(has_text="Successfully created").nth(2).click()

        def add_role():
            page.get_by_role("link", name="Roles").click()
            page.get_by_role("button", name="New Item").click()
            page.get_by_label("Name").fill("New Role")
            page.get_by_label("Description").fill("Basic user role")
            page.get_by_role("combobox").first.click()
            page.get_by_role("option", name="Clear").click()
            page.get_by_role("cell", name="CONFIG_WORKER_ACCESS").click()
            page.get_by_role("cell", name="CONFIG_WORKER_ACCESS").click()
            page.get_by_role("row", name="CONFIG_WORKER_ACCESS Access").get_by_role("cell").first.click()
            page.get_by_role("row", name="ADMIN_OPERATIONS Admin").get_by_role("cell").first.click()
            page.get_by_role("row", name="ANALYZE_ACCESS Analyze access").get_by_role("cell").first.click()
            page.get_by_role("row", name="ANALYZE_CREATE Analyze create").get_by_role("cell").first.click()
            page.get_by_role("row", name="ANALYZE_DELETE Analyze delete").get_by_role("cell").first.click()
            page.get_by_role("row", name="ANALYZE_UPDATE Analyze update").get_by_role("cell").first.click()
            page.get_by_role("row", name="ASSESS_ACCESS Assess access").get_by_role("cell").first.click()
            time.sleep(1)
            page.screenshot(path="./tests/playwright/screenshots/docs_organization_edit_user_role.png")
            page.get_by_role("button", name="Submit").click()
            page.pause()
            expect(page.get_by_text("Successfully created new role")).to_be_visible()
            page.locator("div").filter(has_text="Successfully created new role").nth(2).click()

        def add_user():
            page.get_by_role("link", name="Users").click()
            page.get_by_role("button", name="New Item").click()
            page.get_by_label("Username").click()
            page.get_by_label("Username").fill("test")
            page.get_by_label("Name", exact=True).fill("test")
            page.get_by_label("Password", exact=True).fill("testasdfasdf")
            page.get_by_role("combobox").first.click()
            page.get_by_text("The Clacks").click()
            time.sleep(0.3)
            page.pause()
            page.screenshot(path="./tests/playwright/screenshots/docs_organization_add_new_user.png")
            page.get_by_role("button", name="Submit").click()
            page.locator("div").filter(has_text="New user was successfully added").nth(2).click()

        add_organization()
        add_role()
        add_user()

    def test_admin_osint_workflow(self, taranis_frontend: Page):
        page = taranis_frontend

        def add_osint_sources():
            page.get_by_role("link", name="OSINTSources").click()
            page.get_by_role("button", name="New Item").click()
            time.sleep(1)
            page.screenshot(path="./tests/playwright/screenshots/docs_osint_sources_add.png")
            page.get_by_label("Name").fill("New Source")
            page.locator("#edit_config_form i").nth(3).click()
            page.get_by_text("Simple Web Collector").click()
            page.get_by_label("WEB_URL").click()
            page.get_by_label("WEB_URL").fill("www.example.com")
            page.get_by_role("button", name="Submit").click()
            page.get_by_text("Successfully created New").click()

        def wordlists():
            page.get_by_role("link", name="Word Lists").click()
            time.sleep(1)
            page.screenshot(path="./tests/playwright/screenshots/docs_wordlists.png")
            page.get_by_role("button", name="New Item").click()

        def edit_wordlist():
            page.get_by_role("cell", name="CVE Products").click()
            page.get_by_label("Collector Includelist").check()  # needed to be checked for upcoming tests
            page.get_by_label("Collector Excludelist").check()
            page.get_by_label("Collector Excludelist").uncheck()
            page.get_by_label("Tagging Bot").uncheck()
            page.get_by_label("Tagging Bot").check()
            page.get_by_role("button", name="Submit").click()
            page.locator("div").filter(has_text="updated").nth(2).click()
            page.get_by_role("cell", name="Countries", exact=True).click()
            page.get_by_label("Collector Includelist").check()
            page.get_by_role("button", name="Submit").click()
            page.locator("div").filter(has_text="updated").nth(2).click()
            page.get_by_role("cell", name="Länder", exact=True).click()
            page.get_by_label("Collector Includelist").check()
            page.screenshot(path="./tests/playwright/screenshots/docs_wordlist_usage.png")
            page.get_by_role("button", name="Submit").click()
            page.locator("div").filter(has_text="updated").nth(2).click()

        def enable_wordlists():
            page.get_by_role("link", name="Source Groups").click()
            page.get_by_role("cell", name="Default group for").click()
            page.get_by_role("cell", name="Default", exact=True).click()
            # TODO: Fix wordlists not loading in Admin: Osint Source Groups Settings items
            # page.get_by_role("row", name="CVE Products List of products").get_by_role("cell").first.click()
            # page.get_by_role("row", name="Countries List of Countries").get_by_role("cell").first.click()
            # page.get_by_role("row", name='Länder Liste aller Länder [ "').get_by_role("cell").first.click()
            time.sleep(1)
            page.screenshot(path="./tests/playwright/screenshots/docs_source_groups.png")

        def bots():
            page.get_by_role("link", name="Bots").click()
            page.get_by_role("cell", name="IOC BOT").click()
            page.get_by_role("cell", name="index").click()
            page.get_by_label("Index").click()
            page.locator("div").filter(has_text=re.compile(r"^RUN_AFTER_COLLECTOR$")).nth(3).click()
            time.sleep(0.3)

            page.screenshot(path="./tests/playwright/screenshots/docs_bot_selection.png")

        def osint_sources():
            page.get_by_role("link", name="OSINTSources").click()
            time.sleep(1)
            page.screenshot(path="./tests/playwright/screenshots/docs_osint_sources.png")

        add_osint_sources()
        wordlists()
        edit_wordlist()
        enable_wordlists()
        bots()
        osint_sources()

    def test_admin(self, taranis_frontend: Page):
        pass

    def test_report_types(self, taranis_frontend: Page):
        page = taranis_frontend

        def add_attribute():
            page.get_by_role("link", name="Attributes").click()
            page.get_by_role("button", name="New Item").click()
            page.get_by_label("Name").fill("Test Attribute")
            page.get_by_label("Default Value").fill("0")
            page.get_by_label("Description").fill("Test Description")
            page.locator("#form").get_by_role("combobox").filter(has_text="Type").first.click()
            page.get_by_role("option", name="NUMBER").click()
            time.sleep(0.3)
            page.screenshot(path="./tests/playwright/screenshots/docs_add_attribute.png")
            page.get_by_role("button", name="Submit").click()
            page.locator("div").filter(has_text="created").nth(2).click()

        def new_report_type():
            page.get_by_role("link", name="Report Types").click()
            page.get_by_role("button", name="New Item").click()
            page.get_by_label("Name").fill("Test Report")
            time.sleep(0.3)
            page.screenshot(path="./tests/playwright/screenshots/docs_report_type_add_new_attribute.png")

        def add_attribute_group():
            page.get_by_role("button", name="New Attribute Group").click()
            page.get_by_role("textbox", name="Name").last.fill("Test Attribute Group")
            time.sleep(0.3)
            page.screenshot(path="./tests/playwright/screenshots/docs_report_type_group.png")

        def add_attribute_to_group():
            page.get_by_role("button", name="New Attribute", exact=True).click()
            page.get_by_label("Open").click()
            page.wait_for_load_state("domcontentloaded")
            page.locator("div").filter(has_text=re.compile(r"^MISP Attribute Distribution$")).first.click()
            time.sleep(0.3)
            page.locator('input:below(:text("attribute"))').nth(1).fill("Attribute 1")
            page.get_by_label("Index").fill("1")
            time.sleep(0.3)
            page.screenshot(path="./tests/playwright/screenshots/docs_report_type_select_attribute.png")
            page.get_by_role("button", name="Save").click()

        add_attribute()
        new_report_type()
        add_attribute_group()
        add_attribute_to_group()

    def test_admin_product_types(self, taranis_frontend: Page):
        page = taranis_frontend

        def show_product_type():
            page.get_by_role("link", name="Product Types").click()
            page.get_by_role("cell", name="Default TEXT Presenter").first.click()
            time.sleep(0.3)
            page.screenshot(path="./tests/playwright/screenshots/docs_product_type_edit.png")

        show_product_type()

    def test_user_stories(self, taranis_frontend: Page):
        pass

    def test_dashboard(self, taranis_frontend: Page):
        pass

    def test_open_api(self, taranis_frontend: Page):
        page = taranis_frontend

        def show_open_api():
            page.get_by_role("link", name="OpenAPI").click()
            page.frame_locator('iframe[title="OpenAPI"]').get_by_text("GET/auth/login").click()
            page.screenshot(path="./tests/playwright/screenshots/docs_openapi.png")

        show_open_api()

    def test_publish(self, taranis_frontend: Page):
        page = taranis_frontend

        def show_publish():
            page.get_by_role("link", name="Publish", exact=True).click()
            time.sleep(0.3)
            page.screenshot(path="./tests/playwright/screenshots/docs_publish_panel.png")

        show_publish()

    def test_analyze(self, e2e_server, taranis_frontend: Page):
        from tests.playwright.test_e2e_user import TestEndToEndUser

        page = taranis_frontend

        def delete_multiple_reports():
            page.get_by_role("checkbox").nth(2).click()
            page.get_by_role("checkbox").nth(4).click()
            time.sleep(0.5)
            page.screenshot(path="./tests/playwright/screenshots/docs_report_item_delete_multiple.png")

        e2e = TestEndToEndUser()
        e2e.ci_run = self.ci_run

        e2e.test_e2e_assess(taranis_frontend=page, e2e_server=e2e_server, pic_prefix="docs_")
        print(e2e_server.url())
        e2e.test_e2e_analyze(e2e_server=e2e_server, taranis_frontend=page, pic_prefix="docs_")

        delete_multiple_reports()
