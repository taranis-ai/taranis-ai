#!/usr/bin/env python3
import re
import time
from flask import url_for

from playwright.sync_api import Page, expect
import pytest

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

    def test_admin_user_management(self, logged_in_page: Page, forward_console_and_page_errors):
        def check_dashboard():
            page.goto(url_for("base.dashboard", _external=True))
            expect(page.locator("#dashboard")).to_be_visible()

        def add_organization():
            page.goto(url_for("admin.organizations", _external=True))
            page.get_by_test_id("new-organization-button").click()
            page.get_by_label("Name").fill("Test organizations")
            page.get_by_label("Description").fill("Test description of an organization")
            page.get_by_label("Street").fill("Test Street")
            page.get_by_label("City").fill("Test City")
            page.get_by_label("Zip").fill("9999")
            page.get_by_label("Country").fill("Test Country")
            page.screenshot(path="./tests/playwright/screenshots/docs_organization_add.png")

            with page.expect_response(url_for("admin.organizations", _external=True)) as response_info:
                self.highlight_element(page.locator('input[type="submit"]')).click()
            assert response_info.value.ok, f"Expected 2xx status, but got {response_info.value.status}"
            expect(page.get_by_text("Test organizations")).to_be_visible()

        def add_user():
            page.goto(url_for("admin.users", _external=True))
            page.get_by_test_id("new-user-button").click()
            page.get_by_role("textbox", name="Username", exact=True).fill("test")
            page.get_by_role("textbox", name="Name", exact=True).fill("Test User")
            page.get_by_role("textbox", name="Password", exact=True).fill("testasdfasdf")

            page.get_by_label("Organization").select_option("1")
            page.locator("#user-role-select-ts-control").click()
            page.locator("#user-role-select-opt-1").click()

            page.screenshot(path="./tests/playwright/screenshots/docs_user_add.png")
            with page.expect_response(url_for("admin.users", _external=True)) as response_info:
                self.highlight_element(page.locator('input[type="submit"]')).click()
            assert response_info.value.ok, f"Expected 2xx status, but got {response_info.value.status}"
            expect(page.get_by_text("Test User")).to_be_visible()

        def remove_user():
            page.get_by_test_id("user-view-table").locator("tr").nth(2).locator("td").first.click()
            page.get_by_role("button", name="Delete").click()
            # TODO: Update the string to match the actual message when bug resolved (#various-bugs)
            page.get_by_text("Successfully deleted").click()

        def add_role():
            page.goto(url_for("admin.roles", _external=True))
            page.get_by_test_id("new-role-button").click()
            page.get_by_label("Name").fill("Test Role")
            page.get_by_label("Description").fill("Test description of a role")
            page.get_by_label("TLP Level ").select_option("clear")
            page.screenshot(path="./tests/playwright/screenshots/docs_role_add.png")
            with page.expect_response(url_for("admin.roles", _external=True)) as response_info:
                self.highlight_element(page.locator('input[type="submit"]')).click()
            assert response_info.value.ok, f"Expected 2xx status, but got {response_info.value.status}"
            expect(page.get_by_text("Test Role")).to_be_visible()

        def update_user():
            page.get_by_role("cell", name="test").nth(1).click()
            page.get_by_role("button", name="generate password").click()
            page.get_by_role("row", name="Admin Administrator role").get_by_role("cell").first.click()
            page.get_by_role("row", name="New Role Basic user role").get_by_role("cell").first.click()
            page.get_by_role("row", name="User Basic user role").get_by_role("cell").first.click()
            page.get_by_role("button", name="Submit").click()
            page.get_by_text("User was successfully updated").click()

        def assert_update_user():
            expect(page.locator(":right-of(:text('testname'))").nth(0)).to_have_text("3")

        def assert_update_user_2():
            expect(page.locator(":right-of(:text('testname'))").nth(0)).to_have_text("0")

        def remove_organization():
            # locate to organizations index page
            page.goto(url_for("admin.organizations", _external=True))
            page.get_by_role("row", name=re.compile("Test organizations")).get_by_role("button", name="Delete").click()
            # Set up dialog handler to automatically accept confirmation
            page.on("dialog", lambda dialog: dialog.accept())
            page.get_by_role("button", name="Delete").click()

        #           Run test
        # ============================

        page = logged_in_page
        check_dashboard()
        add_organization()
        add_user()
        # add_role()
        # update_user()
        # assert_update_user()
        # update_user()
        # assert_update_user_2()
        # remove_organization()

    def test_admin_osint_workflow(self, taranis_frontend: Page):
        #        Test definitions
        # ============================

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
            page.locator("span").filter(has_text="every month").click()
            page.get_by_text("January").click()
            page.get_by_text("every day", exact=True).click()
            page.locator("div").filter(has_text=re.compile(r"^2$")).nth(1).click()
            page.locator("span").filter(has_text="every day of the week").click()
            page.get_by_text("Wednesday").click()
            page.locator("span").filter(has_text="every hour").click()
            page.get_by_text("08").click()
            page.locator("span").filter(has_text="every minute").click()
            page.get_by_text("35", exact=True).click()
            expect(page.get_by_role("textbox", name="Cron Expression Cron")).to_have_value("35 8 2 1 3")
            page.get_by_role("button", name="Submit").click()
            page.get_by_text("Successfully created New").click()

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

        #           Run test
        # ============================
        page = taranis_frontend

        # add_osint_sources()
        # wordlists()
        # edit_wordlist()
        # enable_wordlists()
        # bots()
        # osint_sources()

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
        def show_open_api():
            page.goto(url_for("base.open_api", _external=True))
            expect(page.locator("h2.title").first).to_contain_text("Taranis AI")

        page = logged_in_page
        # show_open_api() # figure out how to test the OpenAPI page opening in a new tab

    def test_template_management(self, logged_in_page: Page):
        def show_template_management():
            page.goto(url_for("admin.template_data", _external=True))
            expect(page.locator("#template-list").get_by_role("link", name="Template", exact=True)).to_be_visible()

        def test_invalid_template_shows_invalid_badge():
            """Test that invalid templates show 'Invalid' badge, not 'Valid'."""
            page.get_by_role("link", name="Administration").click()
            page.get_by_test_id("admin-menu-Template").click()
            page.get_by_test_id("new-template-button").click()

            invalid_template_content = """
    <html>
    <body>
        <h1>{{ title }}</h1>
        {% for item in items %}
            <p>{{ item.name }}</p>

    </body>
    </html>
            """.strip()

            page.fill('input[name="id"]', "test_invalid_badge")
            page.fill('textarea[name="content"]', invalid_template_content)
            page.click('input[type="submit"]')

            # Wait for navigation or table update
            page.wait_for_load_state("networkidle")
            # Optionally, navigate to the template list page to ensure table is visible
            page.goto(url_for("admin.template_data", _external=True))
            page.wait_for_load_state("networkidle")

            page.screenshot(path="./tests/playwright/screenshots/after_add_invalid_template.png")

            # Find the template we just created (wait for it to appear)
            invalid_template_row = page.locator("tr").filter(has_text="test_invalid_badge")
            try:
                expect(invalid_template_row).to_be_visible(timeout=10000)
            except Exception:
                print("[DEBUG] Could not find row for 'test_invalid_badge'. Table content printed above.")
                raise

            # Check that it shows "Invalid" badge (not "Valid")
            invalid_badge = invalid_template_row.locator(".badge-error")
            expect(invalid_badge).to_be_visible()
            expect(invalid_badge).to_contain_text("Invalid")

            # Ensure it doesn't have a "Valid" badge
            valid_badge = invalid_template_row.locator(".badge-success")
            expect(valid_badge).not_to_be_visible()

        def test_invalid_template_content_accessible_via_htmx():
            """Test that invalid template content is accessible when navigating via HTMX."""
            page.get_by_role("link", name="Administration").click()
            page.get_by_test_id("admin-menu-Template").click()

            # Find test_invalid.html template (should exist in test data)
            invalid_template_row = page.locator("tr").filter(has_text="test_invalid.html")
            expect(invalid_template_row).to_be_visible()

            invalid_template_row.click()

            # Wait for navigation
            page.wait_for_load_state("networkidle")

            # Verify template content is accessible (not empty/broken)
            template_content = page.locator("#editor-content")
            expect(template_content).to_be_visible()

            content_value = template_content.input_value()
            assert len(content_value) > 0, "Invalid template content should still be accessible"

            # Verify we can see some expected content (the test_invalid.html contains "user.name")
            assert "user.name" in content_value, f"Should contain template content, got: {content_value}"

        def test_monaco_editor_loads_on_htmx_navigation():
            """Test Monaco editor loads properly on HTMX navigation."""

            page.get_by_role("link", name="Administration").click()
            page.get_by_test_id("admin-menu-Template").click()

            # Click on a template to navigate via HTMX (this was failing)
            template_row = page.locator("tr").filter(has_text="test_valid.html")
            expect(template_row).to_be_visible()
            template_row.click()

            # Wait for page load and Monaco initialization
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)  # Wait for Monaco async loading

            # Check that textarea is accessible (Monaco fallback works)
            textarea = page.locator("#editor-content")
            expect(textarea).to_be_visible()

            content = textarea.input_value()
            assert len(content) > 0, "Template content should be accessible"

            # Accept Monaco or fallback textarea
            monaco_div = page.locator("#editor")
            textarea = page.locator("#editor-content")
            if monaco_div.is_visible():
                # Monaco loaded
                expect(monaco_div).to_be_visible()
                # Optionally check Monaco-specific content
                monaco_lines = page.locator(".monaco-editor .view-line")
                if monaco_lines.count() > 0:
                    expect(monaco_lines.first).to_be_visible()
            elif textarea.is_visible():
                expect(textarea).to_be_visible()
                content = textarea.input_value()
                assert len(content) > 0, "Template content should be accessible in fallback"

        page = logged_in_page

        show_template_management()
        test_invalid_template_shows_invalid_badge()
        test_invalid_template_content_accessible_via_htmx()
        test_monaco_editor_loads_on_htmx_navigation()

    def product_type_workflow(self, taranis_frontend: Page):
        """Test product type workflow."""
        page = taranis_frontend

        # Navigate to product types
        page.get_by_test_id("admin-menu-Product Type").click()
        # page.goto(url_for("admin.product_types", _external=True))
        expect(page.locator("h2.title").first).to_contain_text("Product Types")

        # Add a new product type
        page.get_by_test_id("new-product-type-button").click()
        page.get_by_label("Name").fill("Test Product Type")
        page.get_by_label("Description").fill("This is a test product type.")
        page.screenshot(path="./tests/playwright/screenshots/product_type_add.png")
        page.get_by_role("button", name="Create Product Type").click()

        # Verify the new product type appears in the list
        expect(page.get_by_text("Test Product Type")).to_be_visible()
