#!/usr/bin/env python3
import json
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
            expect(page.get_by_role("link", name="Updated description of an organization")).to_be_visible()

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
            page.get_by_role("searchbox", name="Select roles").click()
            page.get_by_role("option", name="User - Basic user role Press").click()

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

    def test_admin_osint_workflow(self, logged_in_page: Page, forward_console_and_page_errors, test_osint_source):
        page = logged_in_page
        osint_source_name = f"test_source_{uuid.uuid4().hex[:6]}"

        def load_osint_sources():
            page.goto(url_for("admin.osint_sources", _external=True))
            expect(page.get_by_role("button", name="Load default OSINT Source")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_osint_sources.png")

        def load_and_search_default_sources():
            page.get_by_role("button", name="Load default OSINT Source").click()
            osint_table = page.get_by_test_id("osint_source-table")
            all_rows = osint_table.locator("tbody tr")
            expect(all_rows).to_have_count(10)

            # search
            page.get_by_placeholder("Search...").fill("news")
            expect(all_rows).to_have_count(1)
            page.get_by_placeholder("Search...").fill("")
            expect(all_rows).to_have_count(10)

            page.get_by_role("row", name="Icon State Name Feed Actions").get_by_role("checkbox").check()
            delete_button = page.get_by_test_id("delete-osint_source-button")
            expect(delete_button).to_contain_text("Delete 10 OSINT Source")
            self.highlight_element(delete_button).click()
            page.get_by_role("button", name="OK").click()
            page.get_by_role("alert").click()

        def import_export_osint_sources():
            page.get_by_role("button", name="Import").click()
            page.get_by_role("button", name="Choose File").set_input_files(test_osint_source)
            page.get_by_role("button", name="Submit").click()
            with page.expect_download() as download_info:
                page.get_by_role("link", name="Export").click()
            assert download_info.value is not None
            download_path = download_info.value.path()
            with open(test_osint_source, "r") as f:
                original_content = json.load(f)
            with open(download_path, "r") as f:
                downloaded_content = json.load(f)
            assert original_content == downloaded_content, "Downloaded file content does not match uploaded file content"
            page.get_by_role("row", name="Icon State Name Feed Actions").get_by_role("checkbox").check()
            page.get_by_test_id("delete-osint_source-button").click()
            page.get_by_role("button", name="OK").click()
            page.get_by_role("alert").click()

        def add_osint_sources():
            page.get_by_test_id("new-osint_source-button").click()
            page.get_by_label("Name").fill(osint_source_name)
            page.get_by_label("Description").fill("Test description of an OSINT source")
            page.get_by_label("Collector Type Select a").select_option("rss_collector")
            page.get_by_role("textbox", name="FEED_URL").fill("http://example.com/feed")
            page.screenshot(path="./tests/playwright/screenshots/docs_osint_sources_add.png")
            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page.get_by_role("link", name=osint_source_name)).to_be_visible()

        def update_osint_sources():
            page.get_by_role("link", name=osint_source_name).click()
            page.get_by_role("textbox", name="FEED_URL").fill("http://example.com/updated_feed_url")

            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page.get_by_role("link", name="http://example.com/updated_feed_url")).to_be_visible()

        def remove_osint_sources():
            page.get_by_role("row", name=osint_source_name).get_by_role("button").last.click()
            page.get_by_role("button", name="Delete").click()
            expect(page.get_by_test_id("osint_source-table").get_by_role("link", name=osint_source_name)).not_to_be_visible()

        load_osint_sources()
        load_and_search_default_sources()
        import_export_osint_sources()
        add_osint_sources()
        update_osint_sources()
        remove_osint_sources()

    def test_admin_osint_source_group_management(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page
        osint_group_name = f"test_osint_group_{uuid.uuid4().hex[:6]}"

        def load_osint_source_groups():
            page.goto(url_for("admin.osint_source_groups", _external=True))
            expect(page.get_by_test_id("osint_source_group-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_osint_source_groups.png")

        def add_osint_source_group():
            page.get_by_test_id("new-osint_source_group-button").click()
            page.get_by_role("textbox", name="Name", exact=True).fill(osint_group_name)
            page.get_by_role("textbox", name="Description", exact=True).fill("Test description of an OSINT source group")
            page.screenshot(path="./tests/playwright/screenshots/docs_osint_source_group_add.png")
            with page.expect_response(url_for("admin.osint_source_groups", _external=True)) as response_info:
                self.highlight_element(page.locator('input[type="submit"]')).click()
            assert response_info.value.ok, f"Expected 2xx status, but got {response_info.value.status}"
            expect(page.get_by_role("link", name=osint_group_name)).to_be_visible()

        def update_osint_source_group():
            page.get_by_role("link", name=osint_group_name).click()
            page.get_by_role("textbox", name="Description", exact=True).fill("Updated description of an OSINT source group")

            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page.get_by_role("link", name="Updated description of an OSINT source group")).to_be_visible()

        def remove_osint_source_group():
            page.get_by_role("row", name=osint_group_name).get_by_role("button").click()
            page.get_by_role("button", name="OK").click()
            expect(page.get_by_test_id("osint_source_group-table").get_by_role("link", name=osint_group_name)).not_to_be_visible()

        load_osint_source_groups()
        add_osint_source_group()
        update_osint_source_group()
        remove_osint_source_group()

    def test_admin_role_management(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        role_name = f"test_role_{uuid.uuid4().hex[:6]}"

        def load_role_list():
            page.goto(url_for("admin.roles", _external=True))
            expect(page.get_by_test_id("role-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_roles.png")

        def add_role():
            page.get_by_test_id("new-role-button").click()
            expect(page.locator("#role-form")).to_be_visible()

            page.get_by_role("textbox", name="Name", exact=True).fill(role_name)
            page.get_by_role("textbox", name="Description", exact=True).fill("Test description of a role")
            page.get_by_label("TLP Level").select_option("green")

            page.locator("th").first.get_by_role("checkbox").check()

            page.screenshot(path="./tests/playwright/screenshots/docs_roles_add.png")
            with page.expect_response(url_for("admin.roles", _external=True)) as response_info:
                self.highlight_element(page.locator('input[type="submit"]')).click()
            assert response_info.value.ok, f"Expected 2xx status, but got {response_info.value.status}"
            expect(page.get_by_role("link", name=role_name)).to_be_visible()

        def update_role():
            page.get_by_role("link", name=role_name).click()
            expect(page.locator("#role-form")).to_be_visible()

            page.get_by_role("textbox", name="Description", exact=True).fill("Updated description of a role")
            page.get_by_label("TLP Level").select_option("amber+strict")

            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page.get_by_role("link", name="Updated description of a role")).to_be_visible()

        def remove_role():
            page.get_by_role("row", name=role_name).get_by_role("button").click()
            page.get_by_role("button", name="OK").click()
            expect(page.get_by_test_id("role-table").get_by_role("link", name=role_name)).not_to_be_visible()

        load_role_list()
        add_role()
        update_role()
        remove_role()

    def test_admin_wordlist_management(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        word_list_name = f"test_word_list_{uuid.uuid4().hex[:6]}"

        def load_word_list():
            page.goto(url_for("admin.word_lists", _external=True))
            expect(page.get_by_role("button", name="Load default Word List")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_word_lists.png")

        def load_default_word_list():
            page.get_by_role("button", name="Load default Word List").click()
            page.get_by_role("row", name="Name Description Words Actions").get_by_role("checkbox").check()
            delete_button = page.get_by_test_id("delete-word_list-button")
            expect(delete_button).to_contain_text("Delete 9 Word List")
            self.highlight_element(delete_button).click()
            page.get_by_role("button", name="OK").click()

        def add_word_list():
            page.get_by_test_id("new-word_list-button").click()
            expect(page.locator("#word_list-form")).to_be_visible()

            page.get_by_role("textbox", name="Name", exact=True).fill(word_list_name)
            page.get_by_role("textbox", name="Description", exact=True).fill("Test description of a word list")
            page.get_by_role("textbox", name="Link", exact=True).fill("http://example.com")
            page.locator("input[name='usage[]'][value='COLLECTOR_INCLUDELIST']").check()

            page.screenshot(path="./tests/playwright/screenshots/docs_word_list_add.png")
            with page.expect_response(url_for("admin.word_lists", _external=True)) as response_info:
                self.highlight_element(page.locator('input[type="submit"]')).click()
            assert response_info.value.ok, f"Expected 2xx status, but got {response_info.value.status}"
            expect(page.get_by_role("link", name=word_list_name)).to_be_visible()

        def update_word_list():
            page.get_by_role("link", name=word_list_name).click()
            expect(page.locator("#word_list-form")).to_be_visible()

            page.get_by_role("textbox", name="Description", exact=True).fill("Updated description of a word list")
            page.locator("input[name='usage[]'][value='TAGGING_BOT']").check()

            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page.get_by_role("link", name="Updated description of a word list")).to_be_visible()

        def remove_word_list():
            page.get_by_role("row", name=word_list_name).get_by_role("button").click()
            page.get_by_role("button", name="OK").click()
            # expect(page.get_by_test_id("word_list-table").get_by_role("link", name=word_list_name)).not_to_be_visible() # TODO: Wordlist table not rendered afer last element is deleted

        load_word_list()
        load_default_word_list()
        add_word_list()
        update_word_list()
        remove_word_list()

    # TODO: remove pre_seed_report_type_all_attribute_types once cache invalidation on backend changes is implemented (needed for check_various_report_type_fields())
    def test_report_types(
        self,
        logged_in_page: Page,
        forward_console_and_page_errors,
        pre_seed_report_type_all_attribute_types_optional,
        pre_seed_report_type_all_attribute_types_required,
    ):
        page = logged_in_page

        report_type_title = f"Test Report {uuid.uuid4().hex[:6]}"
        group_title = "Primary Group"
        attribute_title = "Primary Attribute"

        def load_report_types():
            page.goto(url_for("admin.report_item_types", _external=True))
            expect(page.get_by_test_id("report_item_type-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_report_types.png")

        def add_report_type():
            page.get_by_test_id("new-report_item_type-button").click()
            expect(page.locator("#report_item_type-form")).to_be_visible()

            page.get_by_role("textbox", name="Title", exact=True).fill(report_type_title)
            page.get_by_role("textbox", name="Description", exact=True).fill("Test description of a report item type")

            page.get_by_role("button", name="+ Add New Group").click()
            group_container = page.locator("#attribute-group-0")
            expect(group_container).to_be_visible()
            group_container.locator("input[name$='[title]']").first.fill(group_title)
            group_container.locator("textarea[name$='[description]']").first.fill("Group description")

            group_container.get_by_role("button", name="+ Add New Attribute").click()
            attribute_container = page.locator("#attribute-items-container-0")
            expect(attribute_container.locator("input[name$='[title]']").first).to_be_visible()
            attribute_container.locator("input[name$='[title]']").first.fill(attribute_title)

            attribute_select = attribute_container.locator("select[name$='[attribute_id]']").first
            first_option_value = attribute_select.locator("option:not([disabled])").first.get_attribute("value")
            assert first_option_value, "Expected at least one attribute option"
            attribute_select.select_option(first_option_value)

            attribute_container.locator("input[name$='[description]']").first.fill("Attribute description")
            attribute_required = attribute_container.locator("input[type='checkbox'][name$='[required]']").first
            if not attribute_required.is_checked():
                attribute_required.check()

            page.screenshot(path="./tests/playwright/screenshots/docs_report_types_add.png")
            with page.expect_response(url_for("admin.report_item_types", _external=True)) as response_info:
                self.highlight_element(page.locator('input[type="submit"]')).click()
            assert response_info.value.ok, f"Expected 2xx status, but got {response_info.value.status}"
            expect(page.get_by_role("link", name=report_type_title)).to_be_visible()

        def update_report_type():
            page.get_by_role("link", name=report_type_title).click()
            expect(page.locator("#report_item_type-form")).to_be_visible()

            page.get_by_role("textbox", name="Description", exact=True).fill("Updated description of a report item type")
            group_container = page.locator("#attribute-group-0")
            group_container.locator("textarea[name$='[description]']").first.fill("Updated group description")
            attribute_container = page.locator("#attribute-items-container-0")
            attribute_container.locator("input[name$='[description]']").first.fill("Updated attribute description")

            self.highlight_element(page.locator('input[type="submit"]')).click()
            row = page.get_by_role("row", name=report_type_title)
            expect(row).to_contain_text("Updated description of a report item type")

        def remove_report_type():
            page.get_by_role("row", name=report_type_title).get_by_role("button").click()
            page.get_by_role("button", name="OK").click()
            expect(page.get_by_test_id("report_item_type-table").get_by_role("link", name=report_type_title)).not_to_be_visible()

        load_report_types()
        add_report_type()
        update_report_type()
        remove_report_type()

    def test_product_types(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        product_type_name = f"test_product_type_{uuid.uuid4().hex[:6]}"

        def load_product_types():
            page.goto(url_for("admin.product_types", _external=True))
            expect(page.get_by_test_id("product_type-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_product_types.png")

        def add_product_type():
            page.get_by_test_id("new-product_type-button").click()
            expect(page.locator("#product_type-form")).to_be_visible()

            page.get_by_role("textbox", name="Title", exact=True).fill(product_type_name)
            page.get_by_role("textbox", name="Description", exact=True).fill("Test description of a product type")
            page.get_by_label("Presenter Type Select a").select_option("html_presenter")
            page.get_by_label("TEMPLATE_PATH Select an item").select_option("cert_at_daily_report.html")

            page.get_by_role("searchbox", name="Select report types").click()
            page.get_by_role("option", name="CERT Report").click()

            page.screenshot(path="./tests/playwright/screenshots/docs_product_type_add.png")
            page.get_by_role("searchbox", name="Select report types").press("Escape")
            with page.expect_response(url_for("admin.product_types", _external=True)) as response_info:
                self.highlight_element(page.locator('input[type="submit"]')).click()
            assert response_info.value.ok, f"Expected 2xx status, but got {response_info.value.status}"
            expect(page.get_by_role("link", name=product_type_name)).to_be_visible()

        def update_product_type():
            page.get_by_role("link", name=product_type_name).click()
            expect(page.locator("#product_type-form")).to_be_visible()

            page.get_by_role("textbox", name="Description", exact=True).fill("Updated description of a product type")

            page.locator('input[type="submit"]').click()
            expect(page.get_by_role("link", name="Updated description of a product type")).to_be_visible()

        def remove_product_type():
            page.get_by_role("row", name=product_type_name).get_by_role("button").click()
            page.get_by_role("button", name="OK").click()
            expect(page.get_by_test_id("product_type-table").get_by_role("link", name=product_type_name)).not_to_be_visible()

        load_product_types()
        add_product_type()
        update_product_type()
        remove_product_type()

    def test_open_api(self, logged_in_page: Page):
        page = logged_in_page
        page.goto(url_for("admin.dashboard", _external=True))
        with page.expect_popup() as openapi_info:
            self.highlight_element(page.get_by_role("link", name="OpenAPI")).click()
        openapi_page = openapi_info.value
        expect(openapi_page.locator("iframe").content_frame.get_by_role("heading", name="Taranis AI 1.").first).to_be_visible()
