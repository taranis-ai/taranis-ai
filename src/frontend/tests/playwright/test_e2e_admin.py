#!/usr/bin/env python3
import re
import time
import uuid
import pytest
from flask import url_for

from playwright.sync_api import Page, expect
from playwright_helpers import PlaywrightHelpers


@pytest.mark.e2e_admin
@pytest.mark.e2e_ci
@pytest.mark.usefixtures("e2e_ci")
class TestEndToEndAdmin(PlaywrightHelpers):
    """End-to-end tests for the Taranis AI admin interface."""

    def test_login(self, taranis_frontend: Page):
        page = taranis_frontend
        self.add_keystroke_overlay(page)

        page.goto(url_for("base.login", _external=True))
        expect(page).to_have_title("Taranis AI", timeout=5000)

        self.highlight_element(page.get_by_placeholder("Username"))
        page.get_by_placeholder("Username").fill("admin")
        self.highlight_element(page.get_by_placeholder("Password"))
        page.get_by_placeholder("Password").fill("admin")
        page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")
        self.highlight_element(page.get_by_test_id("login-button")).click()
        expect(page.locator("#dashboard")).to_be_visible()

    def test_admin_dashboard(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        page.goto(url_for("base.dashboard", _external=True))
        expect(page.locator("#dashboard")).to_be_visible()

    def test_admin_organizations(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page
        organization_name = f"test_org_{uuid.uuid4().hex[:6]}"

        def load_organization_list():
            page.goto(url_for("admin.organizations", _external=True))
            expect(page.get_by_test_id("organization-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_organizations.png")

        def add_organization():
            page.get_by_test_id("new-organization-button").click()
            page.get_by_label("Name").fill(organization_name)
            page.get_by_label("Description").fill("Test description of an organization")
            page.get_by_label("Street").fill("Test Street")
            page.get_by_label("City").fill("Test City")
            page.get_by_label("Zip").fill("9999")
            page.get_by_label("Country").fill("Test Country")
            page.screenshot(path="./tests/playwright/screenshots/docs_organization_add.png")

            with page.expect_response(url_for("admin.organizations", _external=True)) as response_info:
                self.highlight_element(page.locator('input[type="submit"]')).click()
            assert response_info.value.ok, f"Expected 2xx status, but got {response_info.value.status}"
            expect(page.get_by_text(organization_name)).to_be_visible()

        def update_organization():
            page.get_by_role("link", name=organization_name).click()
            page.get_by_label("Description").fill("Updated description of an organization")

            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page.get_by_text("Updated description of an organization")).to_be_visible()

        def remove_organization():
            page.get_by_role("row", name=organization_name).get_by_role("button").click()
            page.get_by_role("button", name="OK").click()
            expect(page.get_by_test_id("organization-table").get_by_role("link", name=organization_name)).not_to_be_visible()

        load_organization_list()
        add_organization()
        update_organization()
        remove_organization()

    def test_admin_user_management(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page
        username = f"test_user_{uuid.uuid4().hex[:6]}"

        def load_user_list():
            page.goto(url_for("admin.users", _external=True))
            expect(page.get_by_test_id("user-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_users.png")

        def add_user():
            page.get_by_test_id("new-user-button").click()
            page.get_by_role("textbox", name="Username", exact=True).fill(username)
            page.get_by_role("textbox", name="Name", exact=True).fill("Test User")
            page.get_by_role("textbox", name="Password", exact=True).fill("testasdfasdf")

            page.get_by_label("Organization").select_option("1")
            page.locator("#user-role-select-ts-control").click()
            page.locator("#user-role-select-opt-2").click()

            page.screenshot(path="./tests/playwright/screenshots/docs_user_add.png")
            with page.expect_response(url_for("admin.users", _external=True)) as response_info:
                self.highlight_element(page.locator('input[type="submit"]')).click()
            assert response_info.value.ok, f"Expected 2xx status, but got {response_info.value.status}"
            expect(page.get_by_role("link", name=username)).to_be_visible()

        def update_user():
            page.get_by_role("link", name=username).click()
            page.get_by_role("button", name="Generate Password").click()
            page.get_by_role("textbox", name="Name", exact=True).fill("Test User Updated")
            page.locator('input[type="submit"]').click()
            expect(page.get_by_role("link", name="Test User Updated")).to_be_visible()

        def remove_user():
            page.get_by_role("row", name=username).get_by_role("button").click()
            page.get_by_role("button", name="OK").click()
            expect(page.get_by_test_id("user-table").get_by_role("link", name=username)).not_to_be_visible()

        load_user_list()
        add_user()
        update_user()
        remove_user()

    def test_admin_template_management(self, logged_in_page: Page):
        page = logged_in_page
        template_name = f"test_template_{uuid.uuid4().hex[:6]}"
        valid_template_content = """
          <html>
          <body>
              <h1>{{ title }}</h1>
              {% for item in items %}
                  <p>{{ item.name }}</p>
              {% endfor %}
          </body>
          </html>
        """.strip()

        invalid_template_content = """
          <html>
          <body>
              <h1>{{ title }}</h1>
              {% for item in items %}
                  <p>{{ item.name }}</p>

          </body>
          </html>
        """.strip()

        def load_template_list():
            page.goto(url_for("admin.template_data", _external=True))
            expect(page.get_by_test_id("template-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_templates.png")

        def add_template():
            page.get_by_test_id("new-template-button").click()
            page.get_by_role("textbox", name="Filename", exact=True).fill(template_name)
            page.get_by_role("code").first.fill(valid_template_content)

            page.screenshot(path="./tests/playwright/screenshots/docs_user_add.png")
            with page.expect_response(url_for("admin.template_data", _external=True)) as response_info:
                self.highlight_element(page.locator('input[type="submit"]')).click()
            assert response_info.value.ok, f"Expected 2xx status, but got {response_info.value.status}"
            expect(page.get_by_text(template_name)).to_be_visible()

        def update_template():
            page.get_by_role("link", name=template_name).click()
            page.get_by_role("code").first.fill(invalid_template_content)
            page.locator('input[type="submit"]').click()
            expect(page.get_by_text("invalid")).to_be_visible()

        def remove_template():
            page.get_by_role("row", name=template_name).get_by_role("button").click()
            page.get_by_role("button", name="OK").click()
            expect(page.get_by_test_id("template-table").get_by_role("link", name=template_name)).not_to_be_visible()

        load_template_list()
        # Disabled until https://github.com/microsoft/monaco-editor/issues/5015 is resolved
        # add_template()
        # update_template()
        # remove_template()

    def test_admin_osint_workflow(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page
        osint_source_name = f"test_source_{uuid.uuid4().hex[:6]}"

        def load_osint_sources():
            page.goto(url_for("admin.osint_sources", _external=True))
            expect(page.get_by_role("button", name="Load default OSINT Source")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_osint_sources.png")

        def load_default_sources():
            page.get_by_role("button", name="Load default OSINT Source").click()
            page.get_by_role("row", name="Icon State Name Feed Actions").get_by_role("checkbox").check()
            delete_button = page.get_by_test_id("delete-osint_source-button")
            expect(delete_button).to_contain_text("Delete 10 OSINT Source")
            self.highlight_element(delete_button).click()
            page.get_by_role("button", name="OK").click()

        def add_osint_sources():
            page.get_by_test_id("new-osint_source-button").click()
            page.get_by_label("Name").fill(osint_source_name)
            page.get_by_label("Description").fill("Test description of an OSINT source")
            page.get_by_label("Collector Type Select a").select_option("rss_collector")
            page.get_by_role("textbox", name="FEED_URL").fill("http://example.com/feed")
            page.screenshot(path="./tests/playwright/screenshots/docs_osint_sources_add.png")
            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page.get_by_role("link", name=osint_source_name)).to_be_visible()

        load_osint_sources()
        load_default_sources()
        add_osint_sources()

    def test_admin_wordlist_management(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        def wordlists():
            page.get_by_role("link", name="Word Lists").click()
            time.sleep(1)
            page.screenshot(path="./tests/playwright/screenshots/docs_wordlists.png")

        def edit_wordlist():
            page.get_by_role("button", name="load default lists").click()
            page.get_by_role("button", name="New Item").click()
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

    def test_report_types(self, taranis_frontend: Page):
        #        Test definitions
        # ===============================

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

        #           Run test
        # ============================
        page = taranis_frontend

        # add_attribute()
        # new_report_type()
        # add_attribute_group()
        # add_attribute_to_group()

    def test_open_api(self, logged_in_page: Page):
        page = logged_in_page
        page.goto(url_for("admin.dashboard", _external=True))
        with page.expect_popup() as openapi_info:
            self.highlight_element(page.get_by_role("link", name="OpenAPI")).click()
        openapi_page = openapi_info.value
        expect(openapi_page.locator("iframe").content_frame.get_by_role("heading", name="Taranis AI 1.").first).to_be_visible()
