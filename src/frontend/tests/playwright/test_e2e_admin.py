#!/usr/bin/env python3
import json
import uuid
from datetime import datetime, timezone

import pytest
import requests
from flask import url_for
from playwright.sync_api import Page, expect
from playwright_helpers import PlaywrightHelpers


def remove_tz(date_time: str) -> str:
    dt = datetime.fromisoformat(date_time)
    if dt.tzinfo is not None and dt.utcoffset() is not None:
        dt = dt.astimezone(timezone.utc)
    dt = dt.replace(tzinfo=None)
    return dt.isoformat()


@pytest.mark.e2e_admin
@pytest.mark.e2e_ci
@pytest.mark.usefixtures("e2e_ci")
class TestEndToEndAdmin(PlaywrightHelpers):
    """End-to-end tests for the Taranis AI admin interface."""

    @staticmethod
    def dismiss_notification_if_visible(page: Page):
        notification = page.locator("#notification-bar [role='alert']")
        if notification.is_visible():
            notification.click()
            expect(notification).to_be_hidden()

    def test_login(self, taranis_frontend: Page):
        page = taranis_frontend
        page.context.clear_cookies()
        self.add_keystroke_overlay(page)

        page.goto(url_for("base.login", _external=True))
        expect(page).to_have_title("Taranis AI", timeout=5000)

        self.highlight_element(page.get_by_placeholder("Username"))
        expect(page.get_by_placeholder("Username")).to_have_attribute("required", "")
        page.get_by_placeholder("Username").fill("admin")
        self.highlight_element(page.get_by_placeholder("Password"))
        expect(page.get_by_placeholder("Password")).to_have_attribute("required", "")
        page.get_by_placeholder("Password").fill("admin")
        page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")
        self.highlight_element(page.get_by_test_id("login-button")).click()
        expect(page.locator("#dashboard")).to_be_visible()

    def test_admin_dashboard(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        page.goto(url_for("base.dashboard", _external=True))
        expect(page.locator("#dashboard")).to_be_visible()

    def test_manual_news_item_invalid_language_shows_notification(self, logged_in_page: Page):
        page = logged_in_page

        page.goto(url_for("assess.get_news_item", news_item_id="0", _external=True))
        expect(page.get_by_role("heading", name="Create manual news item")).to_be_visible()
        create_news_item_url = url_for("assess.create_news_item", _external=True)

        page.get_by_role("textbox", name="Title *").fill("Invalid language test")
        page.get_by_role("textbox", name="Link Providing a URL helps others trace the original source.").fill("http://blubb.xxx")
        page.get_by_role("textbox", name="Language ISO 639 language code").fill("xx")

        with page.expect_response(create_news_item_url) as response_info:
            page.get_by_role("button", name="Create news item").click()

        assert response_info.value.status == 400, f"Expected 400 status, but got {response_info.value.status}"
        expect(page.locator("#notification-bar")).to_contain_text("Invalid BCP 47 language tag")
        expect(page.locator("#news-item-form")).to_be_visible()
        self.dismiss_notification_if_visible(page)

    def test_admin_organizations(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page
        organization_name = f"test_org_{uuid.uuid4().hex[:6]}"

        def load_organization_list():
            page.goto(url_for("admin.organizations", _external=True))
            expect(page.get_by_test_id("organization-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_organizations.png")

        def add_organization():
            page.get_by_test_id("new-organization-button").click()
            expect(page.get_by_label("Name")).to_have_attribute("required", "")
            page.get_by_label("Name").fill(organization_name)
            page.get_by_label("Description").fill("Test description of an organization")
            page.get_by_label("Street").fill("Test Street")
            page.get_by_label("City").fill("Test City")
            page.get_by_label("Zip").fill("9999")
            page.get_by_label("Country").fill("Test Country")
            page.screenshot(path="./tests/playwright/screenshots/docs_organization_add.png")

            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page).to_have_url(url_for("admin.organizations", _external=True))
            expect(page.get_by_text(organization_name)).to_be_visible()

        def update_organization():
            page.get_by_role("link", name=organization_name).click()
            page.get_by_label("Description").fill("Updated description of an organization")

            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page).to_have_url(url_for("admin.organizations", _external=True))
            expect(page.get_by_role("row", name=organization_name)).to_contain_text("Updated description of an organization")

        def remove_organization():
            page.get_by_role("row", name=organization_name).get_by_role("button").click()
            page.get_by_role("button", name="OK").click()
            expect(page.get_by_test_id("organization-table").get_by_role("link", name=organization_name)).not_to_be_visible()

        load_organization_list()
        add_organization()
        update_organization()
        remove_organization()

    def test_admin_user_management(self, logged_in_page: Page, forward_console_and_page_errors, test_user, test_user_list):
        page = logged_in_page
        username = f"test_user_{uuid.uuid4().hex[:6]}"

        def load_user_list():
            page.goto(url_for("admin.users", _external=True))
            expect(page.get_by_test_id("user-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_users.png")

        def add_user():
            page.get_by_test_id("new-user-button").click()

            expect(page.get_by_role("textbox", name="Username", exact=True)).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Username", exact=True).fill(username)
            expect(page.get_by_role("textbox", name="Name", exact=True)).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Name", exact=True).fill("Test User")
            expect(page.get_by_role("textbox", name="Password", exact=True)).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Password", exact=True).fill("testasdfasdf")

            expect(page.locator('select[name="organization"]')).to_have_attribute("required", "")
            page.get_by_label("Organization").select_option("1")
            roles_select = page.locator('select[name="roles[]"]')
            expect(roles_select).to_have_attribute("required", "")
            roles_select.select_option(label="User - Basic user role", force=True)

            page.screenshot(path="./tests/playwright/screenshots/docs_user_add.png")
            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page).to_have_url(url_for("admin.users", _external=True))
            expect(page.get_by_role("link", name=username)).to_be_visible()

        def update_user():
            page.get_by_role("link", name=username).click()
            page.get_by_role("button", name="Generate Password").click()
            expect(page.get_by_role("textbox", name="Name", exact=True)).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Name", exact=True).fill("Test User Updated")
            page.locator('input[type="submit"]').click()
            expect(page).to_have_url(url_for("admin.users", _external=True))
            expect(page.get_by_role("link", name="Test User Updated")).to_be_visible()

        def remove_user():
            page.get_by_role("row", name=username).get_by_role("button").click()
            page.get_by_role("button", name="OK").click()
            expect(page.get_by_test_id("user-table").get_by_role("link", name=username)).not_to_be_visible()

        def import_export_users():
            page.get_by_role("button", name="Import").click()
            page.get_by_role("button", name="Choose File").set_input_files(test_user)
            page.get_by_role("button", name="Submit").click()
            with page.expect_download() as download_info:
                page.get_by_role("link", name="Export").click()
            assert download_info.value is not None
            download_path = download_info.value.path()
            with open(test_user_list, "r") as f:
                imported_user_list_correct = json.load(f)
            with open(download_path, "r") as f:
                downloaded_content = json.load(f)
            assert imported_user_list_correct == downloaded_content, "Downloaded file content does not match uploaded file content"
            page.get_by_role("row", name="Jane Smith").get_by_test_id("action-delete-3").click()
            expect(page.get_by_test_id("user-table").get_by_role("link", name="Jane Smith")).not_to_be_visible()
            page.get_by_role("button", name="OK").click()
            page.get_by_role("row", name="John Doe").get_by_test_id("action-delete-4").click()
            page.get_by_role("button", name="OK").click()
            expect(page.get_by_test_id("user-table").get_by_role("link", name="John Doe")).not_to_be_visible()
            self.dismiss_notification_if_visible(page)

        load_user_list()
        add_user()
        update_user()
        remove_user()
        import_export_users()

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
            expect(page.get_by_role("textbox", name="Filename", exact=True)).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Filename", exact=True).fill(template_name)
            page.locator("#editor").get_by_role("textbox").fill(valid_template_content)

            page.screenshot(path="./tests/playwright/screenshots/docs_user_add.png")
            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page).to_have_url(url_for("admin.template_data", _external=True))
            expect(page.get_by_text(template_name)).to_be_visible()

        def update_template():
            page.get_by_role("link", name=template_name).click()
            page.locator("#editor").get_by_role("textbox").fill(invalid_template_content)
            page.locator('input[type="submit"]').click()
            expect(page).to_have_url(url_for("admin.template_data", _external=True))
            template_row = page.get_by_test_id("template-table").locator("tbody tr").filter(has_text=template_name)
            expect(template_row).to_contain_text("Invalid")

        def remove_template():
            page.get_by_role("row", name=template_name).get_by_role("button").click()
            page.get_by_role("button", name="OK").click()
            expect(page.get_by_test_id("template-table").get_by_role("link", name=template_name)).not_to_be_visible()

        load_template_list()
        add_template()
        update_template()
        remove_template()

    def test_admin_osint_workflow(self, logged_in_page: Page, forward_console_and_page_errors, test_osint_source, test_osint_icon_png):
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

            # search by an actual default source name instead of a stale hardcoded term
            first_source_name = all_rows.first.locator("td").nth(3).inner_text().strip()
            page.get_by_placeholder("Search...").fill(first_source_name)
            expect(all_rows).to_have_count(1)
            expect(all_rows.first).to_contain_text(first_source_name)
            page.get_by_placeholder("Search...").fill("")
            expect(all_rows).to_have_count(10)

            page.get_by_role("row", name="Icon State Name Feed Actions").get_by_role("checkbox").check()
            delete_button = page.get_by_test_id("delete-osint_source-button")
            expect(delete_button).to_contain_text("Delete 10 OSINT Source")
            self.highlight_element(delete_button).click()
            page.get_by_role("button", name="OK").click()
            self.dismiss_notification_if_visible(page)
            expect(page.get_by_role("button", name="Reset Filter")).to_be_visible()

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
            self.dismiss_notification_if_visible(page)

        def add_osint_sources():
            page.get_by_test_id("new-osint_source-button").click()
            expect(page.get_by_label("Name")).to_have_attribute("required", "")
            page.get_by_label("Name").fill(osint_source_name)
            page.get_by_label("Description").fill("Test description of an OSINT source")
            page.locator('input[name="rank"][value="4"]').check()
            feed_url_input = page.locator('input[name="parameters[FEED_URL]"]')
            self.select_dynamic_type_and_wait(page, "rss_collector", "/admin/source_parameters/0", feed_url_input)
            expect(feed_url_input).to_have_attribute("required", "")
            feed_url_input.fill("http://example.com/feed")
            page.screenshot(path="./tests/playwright/screenshots/docs_osint_sources_add.png")
            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page.locator("#osint_source-form")).to_be_visible()
            expect(page.get_by_label("Name")).to_have_value(osint_source_name)

        def update_osint_sources():
            form = page.locator("#osint_source-form").first
            expect(form).to_be_visible()
            expect(form.locator('input[name="rank"][value="4"]')).to_be_checked()
            form.locator('input[name="rank"][value="2"]').check()
            feed_url_input = form.locator('input[name="parameters[FEED_URL]"]')
            expect(feed_url_input).to_have_attribute("required", "")
            feed_url_input.fill("http://example.com/updated-feed-url")
            page.get_by_label("Icon").set_input_files(test_osint_icon_png)

            form.evaluate("form => { form.noValidate = true; }")
            self.highlight_element(form.locator('input[type="submit"]')).click()
            expect(form).to_be_visible()
            expect(page.get_by_test_id("current-osint-icon")).to_be_visible()

            form = page.locator("#osint_source-form").first
            expect(form).to_be_visible()
            expect(form.locator('input[name="rank"][value="2"]')).to_be_checked()
            page.get_by_test_id("delete-osint-icon-on-save").check()

            form.evaluate("form => { form.noValidate = true; }")
            self.highlight_element(form.locator('input[type="submit"]')).click()
            expect(form).to_be_visible()
            expect(page.get_by_label("Name")).to_have_value(osint_source_name)
            page.goto(url_for("admin.osint_sources", _external=True))
            expect(page.get_by_role("link", name="http://example.com/updated-feed-url")).to_be_visible()
            osint_row = page.get_by_role("row", name=osint_source_name)
            expect(osint_row.locator("img.icon")).to_have_count(0)

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

    def test_admin_osint_source_group_management(self, logged_in_page: Page, forward_console_and_page_errors, test_batch_osint_sources):
        page = logged_in_page
        osint_group_name = f"test_osint_group_{uuid.uuid4().hex[:6]}"

        def load_osint_source_groups():
            page.goto(url_for("admin.osint_source_groups", _external=True))
            expect(page.get_by_test_id("osint_source_group-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_osint_source_groups.png")

        def add_osint_source_group():
            page.get_by_test_id("new-osint_source_group-button").click()
            expect(page.get_by_role("textbox", name="Name", exact=True)).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Name", exact=True).fill(osint_group_name)
            page.get_by_role("textbox", name="Description", exact=True).fill("Test description of an OSINT source group")
            page.screenshot(path="./tests/playwright/screenshots/docs_osint_source_group_add.png")
            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page).to_have_url(url_for("admin.osint_source_groups", _external=True))
            expect(page.get_by_role("link", name=osint_group_name)).to_be_visible()

        def update_osint_source_group():
            page.get_by_role("link", name=osint_group_name).click()
            page.get_by_role("textbox", name="Description", exact=True).fill("Updated description of an OSINT source group")

            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page).to_have_url(url_for("admin.osint_source_groups", _external=True))
            expect(page.get_by_role("row", name=osint_group_name)).to_contain_text("Updated description of an OSINT source group")

        def remove_osint_source_group():
            page.get_by_role("row", name=osint_group_name).get_by_role("button").click()
            page.get_by_role("button", name="OK").click()
            expect(page.get_by_test_id("osint_source_group-table").get_by_role("link", name=osint_group_name)).not_to_be_visible()

        def test_page_osint_sources():
            page.goto(url_for("admin.osint_sources", _external=True))
            page.goto(url_for("admin.osint_source_groups", _external=True))
            page.get_by_test_id("new-osint_source_group-button").click()
            source_row = page.locator("#osint_sources tbody tr").first
            expect(source_row).to_be_visible()
            source_name = source_row.locator("td").nth(1).inner_text().strip()
            page.get_by_role("textbox", name="Search...").first.fill(source_name)
            expect(source_row).to_contain_text(source_name)
            source_row.get_by_role("checkbox").check()
            expect(page.locator('input[type="hidden"][name="osint_sources[]"]')).to_have_count(1)

        load_osint_source_groups()
        add_osint_source_group()
        update_osint_source_group()
        remove_osint_source_group()
        test_page_osint_sources()

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

            expect(page.get_by_role("textbox", name="Name", exact=True)).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Name", exact=True).fill(role_name)
            expect(page.get_by_role("textbox", name="Description", exact=True)).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Description", exact=True).fill("Test description of a role")
            expect(page.get_by_label("TLP Level")).to_have_attribute("required", "")
            page.get_by_label("TLP Level").select_option("green")

            page.locator("th").first.get_by_role("checkbox").check()

            page.screenshot(path="./tests/playwright/screenshots/docs_roles_add.png")
            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page).to_have_url(url_for("admin.roles", _external=True))
            expect(page.get_by_role("link", name=role_name)).to_be_visible()

        def update_role():
            page.get_by_role("link", name=role_name).click()
            expect(page.locator("#role-form")).to_be_visible()

            expect(page.get_by_role("textbox", name="Description", exact=True)).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Description", exact=True).fill("Updated description of a role")
            expect(page.get_by_label("TLP Level")).to_have_attribute("required", "")
            page.get_by_label("TLP Level").select_option("amber+strict")

            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page).to_have_url(url_for("admin.roles", _external=True))
            expect(page.get_by_role("row", name=role_name)).to_contain_text("Updated description of a role")

        def remove_role():
            page.get_by_role("row", name=role_name).get_by_role("button").click()
            page.get_by_role("button", name="OK").click()
            expect(page.get_by_test_id("role-table").get_by_role("link", name=role_name)).not_to_be_visible()

        load_role_list()
        add_role()
        update_role()
        remove_role()

    def test_admin_wordlist_management(self, logged_in_page: Page, forward_console_and_page_errors, test_wordlist):
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
            self.dismiss_notification_if_visible(page)

        def add_word_list():
            page.get_by_test_id("new-word_list-button").click()
            expect(page.locator("#word_list-form")).to_be_visible()

            expect(page.get_by_role("textbox", name="Name", exact=True)).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Name", exact=True).fill(word_list_name)
            page.get_by_role("textbox", name="Description", exact=True).fill("Test description of a word list")
            page.get_by_role("textbox", name="Link", exact=True).fill("http://example.com")
            page.locator("input[name='usage[]'][value='COLLECTOR_INCLUDELIST']").check()

            page.screenshot(path="./tests/playwright/screenshots/docs_word_list_add.png")
            self.highlight_element(page.get_by_role("button", name="Create Word List")).click()
            self.dismiss_notification_if_visible(page)
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

        def import_export_word_lists():
            page.get_by_role("button", name="Import").click()
            page.get_by_role("button", name="Choose File").set_input_files(test_wordlist)
            page.get_by_role("button", name="Submit").click()
            with page.expect_download() as download_info:
                page.get_by_role("link", name="Export").click()
            assert download_info.value is not None
            download_path = download_info.value.path()
            with open(test_wordlist, "r") as f:
                imported_user_list_correct = json.load(f)
            with open(download_path, "r") as f:
                downloaded_content = json.load(f)
            assert imported_user_list_correct == downloaded_content, "Downloaded file content does not match uploaded file content"
            page.get_by_role("row", name="Test wordlist").get_by_test_id("action-delete-1").click()
            expect(page.get_by_test_id("user-table").get_by_role("link", name="Test wordlist")).not_to_be_visible()
            page.get_by_role("button", name="OK").click()
            self.dismiss_notification_if_visible(page)

        load_word_list()
        load_default_word_list()
        add_word_list()
        update_word_list()
        remove_word_list()
        import_export_word_lists()

    def test_admin_acls(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page
        acl_table = page.get_by_test_id("acl-table")

        def load_acls():
            page.goto(url_for("admin.acls", _external=True))
            expect(acl_table).to_be_visible()
            expect(page.get_by_test_id("new-acl-button")).to_be_visible()

        def test_acl_create():
            page.get_by_test_id("new-acl-button").click()
            acl_form = page.locator("#acl-form")
            expect(acl_form).to_be_visible()

            name_input = acl_form.locator('input[name="name"]')
            item_type_select = acl_form.locator('select[name="item_type"]')
            item_id_select = acl_form.locator('#item_ids select[name="item_id"]')
            roles_table = acl_form.locator("#roles-table")
            roles_widget = acl_form.locator("#dataTableDiv")

            expect(name_input).to_have_attribute("required", "")
            name_input.fill("Test ACL")
            expect(item_type_select).to_have_attribute("required", "")
            with page.expect_response(
                lambda response: (
                    response.request.method == "GET"
                    and "/admin/acl/item_ids" in response.url
                    and "item_type=osint_source_group" in response.url
                )
            ) as response_info:
                item_type_select.select_option("osint_source_group")
            assert response_info.value.ok, f"Expected successful item load, but got {response_info.value.status}: {response_info.value.url}"
            expect(item_id_select).to_be_enabled()
            expect(item_id_select).to_have_attribute("required", "")

            acl_form.locator('input[name="enabled"][type="checkbox"]').set_checked(False)
            acl_form.locator('input[name="read_only"][type="checkbox"]').set_checked(False)
            roles_table.locator("tbody tr", has_text="Admin Administrator role").locator('input[type="checkbox"]').click()
            expect(roles_widget.locator('input[type="hidden"][name="roles[]"][value="1"]')).to_have_count(1)
            roles_table.locator("tbody tr", has_text="User Basic user role").locator('input[type="checkbox"]').click()
            expect(roles_widget.locator('input[type="hidden"][name="roles[]"][value="2"]')).to_have_count(1)
            page.get_by_role("button", name="Create ACL").click()

        def test_acl_update():
            page.get_by_role("link", name="Test ACL").click()
            acl_form = page.locator("#acl-form")
            expect(acl_form).to_be_visible()

            roles_table = acl_form.locator("#roles-table")
            roles_widget = acl_form.locator("#dataTableDiv")
            expect(roles_widget.locator('input[type="hidden"][name="roles[]"][value="1"]')).to_have_count(1)
            roles_table.locator("tbody tr", has_text="Admin Administrator role").locator('input[type="checkbox"]').click()
            expect(roles_widget.locator('input[type="hidden"][name="roles[]"][value="1"]')).to_have_count(0)
            name_input = acl_form.locator('input[name="name"]')
            expect(name_input).to_have_attribute("required", "")
            name_input.fill("Test ACL updated")
            acl_form.locator('input[name="enabled"][type="checkbox"]').set_checked(True)
            acl_form.locator('input[name="read_only"][type="checkbox"]').set_checked(True)
            page.get_by_role("button", name="Update ACL").click()

        def test_acl_delete():
            acl_row = acl_table.locator("tbody tr", has=page.get_by_role("link", name="Test ACL updated", exact=True)).first
            expect(acl_row).to_be_visible()
            acl_row.locator('[data-testid^="action-delete-"]').click()
            expect(page.get_by_role("dialog", name="Are you sure you want to")).to_be_visible()
            page.get_by_role("button", name="OK").click()
            expect(acl_row).not_to_be_visible()

        load_acls()
        test_acl_create()
        test_acl_update()
        test_acl_delete()

    def test_admin_attributes(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        def load_attributes():
            page.goto(url_for("admin.attributes", _external=True))
            expect(page.get_by_test_id("attribute-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_attributes.png")

        def test_attribute_create():
            page.get_by_role("link", name="Administration").click()

            expect(page.get_by_role("link", name="Taranis AI Logo")).to_be_visible()

            page.get_by_test_id("admin-menu-Attribute").click()
            expect(page.get_by_role("row", name="Attachment Attachment")).to_be_visible()

            page.get_by_test_id("new-attribute-button").click()
            expect(page.get_by_role("heading", name="Create Attribute")).to_be_visible()

            expect(page.get_by_role("textbox", name="Name")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Name").click()
            page.get_by_role("textbox", name="Name").fill("attribute number 5")
            expect(page.get_by_role("textbox", name="Description")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Description").click()
            page.get_by_role("textbox", name="Description").fill("attr 5")
            page.get_by_role("textbox", name="Default Value").click()
            page.get_by_role("textbox", name="Default Value").fill("5")
            expect(page.locator('select[name="type"]')).to_have_attribute("required", "")
            page.get_by_label("Attribute Type Select an item").select_option("number")
            page.get_by_role("button", name="Create Attribute").click()
            expect(page.get_by_role("row", name="Attachment Attachment")).to_be_visible()

            page.get_by_test_id("new-attribute-button").click()
            expect(page.get_by_role("heading", name="Create Attribute")).to_be_visible()

            page.locator("#attribute-list").get_by_role("link", name="Attribute").click()
            expect(page.get_by_role("row", name="Attachment Attachment")).to_be_visible()

            page.get_by_test_id("admin-menu-Report Item Type").click()
            expect(page.get_by_role("row", name="CERT Report Example CERT")).to_be_visible()

            page.get_by_test_id("new-report_item_type-button").click()
            expect(page.get_by_role("heading", name="Create Report Item Type")).to_be_visible()

            expect(page.get_by_role("textbox", name="Title")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Title").click()
            page.get_by_role("textbox", name="Title").fill("report item type test 5")
            expect(page.get_by_role("textbox", name="Description")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Description").click()
            page.get_by_role("textbox", name="Description").fill("atrr5")
            page.get_by_role("button", name="+ Add New Group").click()
            expect(page.get_by_role("spinbutton", name="Group Index")).to_be_visible()

            expect(page.get_by_role("textbox", name="Group Title")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Group Title").click()
            page.get_by_role("textbox", name="Group Title").fill("group1")
            page.get_by_role("textbox", name="Group Description").click()
            page.get_by_role("button", name="+ Add New Attribute").click()
            expect(page.get_by_role("group", name="Required")).to_be_visible()

            expect(page.get_by_role("textbox", name="Attribute Title")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Attribute Title").click()
            page.get_by_role("textbox", name="Attribute Title").fill("attr title text")
            expect(page.locator("select[name$='[attribute_id]']").first).to_have_attribute("required", "")
            page.get_by_label("Attribute Type * Select an").select_option("28")
            page.get_by_role("textbox", name="Attribute Description").click()
            page.get_by_role("textbox", name="Attribute Description").fill("test 5")
            page.get_by_role("textbox", name="Attribute Description").dblclick()
            page.get_by_role("textbox", name="Attribute Description").fill("number 5")
            page.get_by_role("button", name="Create Report Item Type").click()
            expect(page.get_by_role("row", name="CERT Report Example CERT")).to_be_visible()

            page.get_by_role("link", name="Analyze").click()
            expect(page.get_by_role("row", name="Title Created Type Stories")).to_be_visible()

            page.get_by_test_id("new-report-button").click()
            expect(page.get_by_role("heading", name="Create Report")).to_be_visible()

            page.locator(".col-span-12 > .grid > div").first.click()
            expect(page.get_by_role("textbox", name="Title")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Title").fill("number 5 in report")
            page.get_by_label("Report Type Select a report").select_option("6")
            page.get_by_test_id("save-report").click()
            expect(page.get_by_role("heading", name="Update Report - number 5 in")).to_be_visible()
            expect(page.get_by_role("heading", name="group1")).to_be_visible()
            attr_field = page.get_by_role("spinbutton", name="attr title text")
            expect(attr_field).to_have_value("5")

        def test_attribute_update():
            page.get_by_role("link", name="Administration").click()
            expect(page.get_by_role("link", name="Taranis AI Logo")).to_be_visible()

            page.get_by_test_id("admin-menu-Attribute").click()
            expect(page.get_by_role("row", name="Attachment Attachment")).to_be_visible()

            page.get_by_text("›").click()
            expect(page.get_by_role("row", name="Rich Text Rich Text Rich Edit")).to_be_visible()

            page.get_by_role("link", name="attribute number").click()
            expect(page.get_by_role("link", name="Taranis AI Logo")).to_be_visible()

            expect(page.get_by_role("textbox", name="Name")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Name").click()
            page.get_by_role("textbox", name="Name").fill("attribute number 6")
            expect(page.get_by_role("textbox", name="Description")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Description").click()
            page.get_by_role("textbox", name="Description").fill("attr 6")
            page.get_by_role("textbox", name="Default Value").click()
            page.get_by_role("textbox", name="Default Value").fill("6")
            page.get_by_role("button", name="Update Attribute").click()
            expect(page.get_by_role("row", name="Attachment Attachment")).to_be_visible()

            page.get_by_role("link", name="Analyze").click()
            expect(page.get_by_role("row", name="number 5 in report")).to_be_visible()

            page.get_by_test_id("new-report-button").click()
            expect(page.get_by_role("heading", name="Create Report")).to_be_visible()

            page.get_by_role("textbox", name="Title").click()
            expect(page.get_by_role("textbox", name="Title")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Title").fill("update attr use")
            page.get_by_label("Report Type Select a report").select_option("6")
            page.get_by_test_id("save-report").click()
            attr_field = page.get_by_role("spinbutton", name="attr title text")
            expect(attr_field).to_have_value("6")

        def test_attribute_delete():
            page.get_by_role("link", name="Analyze").click()
            expect(page.get_by_role("row", name="update attr use")).to_be_visible()

            for _ in range(2):
                page.locator('[data-testid^="action-delete-"]').first.click()
                expect(page.get_by_role("dialog", name="Are you sure you want to")).to_be_visible()
                page.get_by_role("button", name="OK").click()

            expect(page.get_by_role("row", name="Title Created Type Stories")).to_be_visible()

            page.get_by_role("link", name="Administration").click()
            expect(page.get_by_role("link", name="Taranis AI Logo")).to_be_visible()

            page.get_by_test_id("admin-menu-Report Item Type").click()
            expect(page.get_by_role("row", name="CERT Report Example CERT")).to_be_visible()

            page.get_by_test_id("action-delete-6").click()
            expect(page.get_by_role("dialog", name="Are you sure you want to")).to_be_visible()

            page.get_by_role("button", name="OK").click()
            expect(page.get_by_role("row", name="CERT Report Example CERT")).to_be_visible()

            page.get_by_test_id("admin-menu-Attribute").click()
            expect(page.get_by_role("row", name="Attachment Attachment")).to_be_visible()

            page.get_by_text("›").click()
            expect(page.get_by_role("row", name="Rich Text Rich Text Rich Edit")).to_be_visible()

            page.get_by_test_id("action-delete-28").click()
            expect(page.get_by_role("dialog", name="Are you sure you want to")).to_be_visible()

            page.get_by_role("button", name="OK").click()

        load_attributes()
        test_attribute_create()
        test_attribute_update()
        test_attribute_delete()

    def test_admin_report_types(self, logged_in_page: Page, forward_console_and_page_errors):
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

            expect(page.get_by_role("textbox", name="Title", exact=True)).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Title", exact=True).fill(report_type_title)
            expect(page.get_by_role("textbox", name="Description", exact=True)).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Description", exact=True).fill("Test description of a report item type")

            page.get_by_role("button", name="+ Add New Group").click()
            group_container = page.locator("#attribute-group-0")
            expect(group_container).to_be_visible()
            expect(group_container.locator("input[name$='[title]']").first).to_have_attribute("required", "")
            group_container.locator("input[name$='[title]']").first.fill(group_title)
            group_container.locator("textarea[name$='[description]']").first.fill("Group description")

            group_container.get_by_role("button", name="+ Add New Attribute").click()
            attribute_container = page.locator("#attribute-items-container-0")
            expect(attribute_container.locator("input[name$='[title]']").first).to_be_visible()
            expect(attribute_container.locator("input[name$='[title]']").first).to_have_attribute("required", "")
            attribute_container.locator("input[name$='[title]']").first.fill(attribute_title)

            attribute_select = attribute_container.locator("select[name$='[attribute_id]']").first
            expect(attribute_select).to_have_attribute("required", "")
            first_option_value = attribute_select.locator("option:not([disabled])").first.get_attribute("value")
            assert first_option_value, "Expected at least one attribute option"
            attribute_select.select_option(first_option_value)

            attribute_container.locator("input[name$='[description]']").first.fill("Attribute description")
            attribute_required = attribute_container.locator("input[type='checkbox'][name$='[required]']").first
            if not attribute_required.is_checked():
                attribute_required.check()

            page.screenshot(path="./tests/playwright/screenshots/docs_report_types_add.png")
            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page).to_have_url(url_for("admin.report_item_types", _external=True))
            expect(page.get_by_role("link", name=report_type_title)).to_be_visible()

        def update_report_type():
            page.get_by_role("link", name=report_type_title).click()
            expect(page.locator("#report_item_type-form")).to_be_visible()

            expect(page.get_by_role("textbox", name="Description", exact=True)).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Description", exact=True).fill("Updated description of a report item type")
            group_container = page.locator("#attribute-group-0")
            group_container.locator("textarea[name$='[description]']").first.fill("Updated group description")
            attribute_container = page.locator("#attribute-items-container-0")
            attribute_container.locator("input[name$='[description]']").first.fill("Updated attribute description")

            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page).to_have_url(url_for("admin.report_item_types", _external=True))
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

    def test_admin_product_types(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        product_type_name = f"test_product_type_{uuid.uuid4().hex[:6]}"

        def load_product_types():
            page.goto(url_for("admin.product_types", _external=True))
            expect(page.get_by_test_id("product_type-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_product_types.png")

        def add_product_type():
            page.get_by_test_id("new-product_type-button").click()
            expect(page.locator("#product_type-form")).to_be_visible()

            expect(page.get_by_role("textbox", name="Title", exact=True)).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Title", exact=True).fill(product_type_name)
            page.get_by_role("textbox", name="Description", exact=True).fill("Test description of a product type")
            template_path_select = page.locator('select[name="parameters[TEMPLATE_PATH]"]')
            self.select_dynamic_type_and_wait(page, "html_presenter", "/admin/product_type_parameters/0", template_path_select)
            expect(template_path_select).to_have_attribute("required", "")
            template_path_select.select_option("cert_at_daily_report.html")

            expect(page.locator('select[name="report_types[]"]')).to_have_attribute("required", "")
            page.get_by_role("searchbox", name="Select report types").click()
            page.get_by_role("option", name="CERT Report").click()

            page.screenshot(path="./tests/playwright/screenshots/docs_product_type_add.png")
            page.get_by_role("searchbox", name="Select report types").press("Escape")
            self.highlight_element(page.locator('input[type="submit"]')).click()
            expect(page).to_have_url(url_for("admin.product_types", _external=True))
            expect(page.get_by_role("link", name=product_type_name)).to_be_visible()

        def update_product_type():
            page.get_by_role("link", name=product_type_name).click()
            expect(page.locator("#product_type-form")).to_be_visible()

            page.get_by_role("textbox", name="Description", exact=True).fill("Updated description of a product type")

            page.locator('input[type="submit"]').click()
            expect(page).to_have_url(url_for("admin.product_types", _external=True))
            expect(page.get_by_role("row", name=product_type_name)).to_contain_text("Updated description of a product type")

        def remove_product_type():
            page.get_by_role("row", name=product_type_name).get_by_role("button").click()
            page.get_by_role("button", name="OK").click()
            expect(page.get_by_test_id("product_type-table").get_by_role("link", name=product_type_name)).not_to_be_visible()

        load_product_types()
        add_product_type()
        update_product_type()
        remove_product_type()

    def test_admin_bot(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        def test_load_bots():
            page.goto(url_for("admin.bots", _external=True))
            expect(page.get_by_test_id("bot-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_bots.png")

        def test_bot_create():
            page.get_by_test_id("new-bot-button").click()
            expect(page.get_by_role("heading", name="Create Bot")).to_be_visible()
            refresh_interval_input = page.locator('input[name="parameters[REFRESH_INTERVAL]"]')

            expect(page.get_by_role("textbox", name="Name")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Name").fill("test bot")
            expect(page.get_by_role("textbox", name="Description")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Description").fill("test bot description")
            expect(page.get_by_role("spinbutton", name="Index")).to_have_attribute("required", "")
            page.get_by_role("spinbutton", name="Index").fill("21")
            self.select_dynamic_type_and_wait(page, "nlp_bot", "/admin/bot_parameters/0", refresh_interval_input)

            page.get_by_role("textbox", name="ITEM_FILTER").fill("1")
            page.get_by_role("textbox", name="BOT_API_KEY").fill("2")
            page.get_by_role("textbox", name="REQUESTS_TIMEOUT").fill("30")
            page.get_by_role("textbox", name="BOT_ENDPOINT").fill("http://test.url")

            page.get_by_role("checkbox", name="run_after_collector").check()
            page.get_by_role("button", name="Create Bot").click()

        def test_bot_update():
            page.get_by_role("link", name="test bot", exact=True).click()
            expect(page.locator('input[name="parameters[REFRESH_INTERVAL]"]')).to_be_visible()

            expect(page.get_by_role("textbox", name="Name")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Name").fill("test bot updated")
            expect(page.get_by_role("spinbutton", name="Index")).to_have_attribute("required", "")
            page.get_by_role("spinbutton", name="Index").fill("12")
            page.get_by_role("button", name="Update Bot").click()

            page.get_by_role("link", name="test bot updated").click()
            expect(page.locator('input[name="parameters[REFRESH_INTERVAL]"]')).to_be_visible()

            page.get_by_role("button", name="Update Bot").click()

        def test_remove_bot():
            bot_table = page.get_by_test_id("bot-table")
            all_rows = bot_table.locator("tbody tr")
            expect(all_rows).to_have_count(8)
            bot_table.locator('[data-testid^="action-delete-"]').last.click()
            expect(page.get_by_role("dialog", name="Are you sure you want to")).to_be_visible()
            page.get_by_role("button", name="OK").click()
            self.dismiss_notification_if_visible(page)

        test_load_bots()
        test_bot_create()
        test_bot_update()
        test_remove_bot()

    def test_admin_connector_management(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        connector_name = f"test_connector_{uuid.uuid4().hex[:6]}"
        updated_connector_name = f"{connector_name} updated"

        connector_table = page.get_by_test_id("connector-table")

        def load_connectors():
            page.goto(url_for("admin.connectors", _external=True))
            expect(connector_table).to_be_visible()
            expect(page.get_by_test_id("new-connector-button")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_connectors.png")

        def add_connector():
            page.get_by_test_id("new-connector-button").click()
            expect(page.get_by_test_id("connector-form")).to_be_visible()
            refresh_interval_input = page.locator('input[name="parameters[REFRESH_INTERVAL]"]')

            expect(page.get_by_role("textbox", name="Name")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Name").fill(connector_name)
            self.select_dynamic_type_and_wait(page, "misp_connector", "/admin/connector_parameters/0", refresh_interval_input)

            expect(page.get_by_role("textbox", name="URL")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="URL").fill("test.url")
            expect(page.get_by_role("textbox", name="API_KEY")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="API_KEY").fill("11111")
            expect(page.get_by_role("textbox", name="ORGANISATION_ID")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="ORGANISATION_ID").fill("1")

            page.locator('input[name="parameters[SSL_CHECK]"][type="checkbox"]').set_checked(True)
            page.get_by_role("textbox", name="SHARING_GROUP_ID").fill("0")
            page.get_by_test_id("connector-submit-button").click()
            expect(page.get_by_test_id("connector-form")).to_have_count(0)
            expect(connector_table.get_by_role("link", name=connector_name, exact=True)).to_be_visible()

        def update_connector():
            page.get_by_role("link", name=connector_name).click()
            expect(page.get_by_test_id("connector-form")).to_be_visible()
            expect(page.locator('input[name="parameters[SSL_CHECK]"][type="checkbox"]')).to_be_visible()

            expect(page.get_by_role("textbox", name="Name")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Name").fill(updated_connector_name)
            page.get_by_test_id("connector-submit-button").click()
            expect(page.get_by_test_id("connector-form")).to_have_count(0)
            expect(connector_table.get_by_role("link", name=updated_connector_name, exact=True)).to_be_visible()

        def remove_connector():
            connector_row = connector_table.locator("tbody tr", has=page.get_by_role("link", name=updated_connector_name, exact=True)).first
            expect(connector_row).to_be_visible()
            connector_row.locator('[data-testid^="action-delete-"]').click()
            expect(page.get_by_role("dialog", name="Are you sure you want to")).to_be_visible()
            page.get_by_role("button", name="OK").click()
            expect(connector_row).not_to_be_visible()

        load_connectors()
        add_connector()
        update_connector()
        remove_connector()

    def test_publisher_presets(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        def load_publisher_presets():
            page.goto(url_for("admin.publisher_presets", _external=True))
            expect(page.get_by_test_id("publisher_preset-table")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_publisher_presets.png")

        def publisher_presets_create():
            page.get_by_test_id("new-publisher_preset-button").click()
            expect(page.get_by_role("heading", name="Create Publisher Preset")).to_be_visible()
            ftp_url_input = page.locator('input[name="parameters[FTP_URL]"]')

            expect(page.get_by_role("textbox", name="Name")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Name").fill("publisher preset test")
            self.select_dynamic_type_and_wait(page, "ftp_publisher", "/admin/publisher_parameters/0", ftp_url_input)
            expect(ftp_url_input).to_have_attribute("required", "")
            ftp_url_input.fill("testurl")
            page.get_by_role("button", name="Create Publisher Preset").click()
            expect(page.get_by_role("row", name="publisher preset test Ftp")).to_be_visible()

        def publisher_presets_update():
            page.get_by_role("link", name="publisher preset test").click()
            expect(page.get_by_role("link", name="Taranis AI Logo")).to_be_visible()
            ftp_url_input = page.locator('input[name="parameters[FTP_URL]"]')

            ftp_url_input.click()
            expect(ftp_url_input).to_have_attribute("required", "")
            ftp_url_input.fill("testurl.com")
            page.get_by_role("textbox", name="Name").click()
            expect(page.get_by_role("textbox", name="Name")).to_have_attribute("required", "")
            page.get_by_role("textbox", name="Name").fill("publisher preset test updated")
            page.get_by_role("button", name="Update Publisher Preset").click()
            expect(page.get_by_role("row", name="publisher preset test updated")).to_be_visible()

        def publisher_presets_delete():
            publisher_table = page.get_by_test_id("publisher_preset-table")
            all_rows = publisher_table.locator("tbody tr")
            expect(all_rows).to_have_count(1)
            publisher_table.locator('[data-testid^="action-delete-"]').first.click()

            expect(page.get_by_role("dialog", name="Are you sure you want to")).to_be_visible()

            page.get_by_role("button", name="OK").click()
            expect(publisher_table.get_by_role("link", name="publisher preset test updated")).not_to_be_visible()

        load_publisher_presets()
        publisher_presets_create()
        publisher_presets_update()
        publisher_presets_delete()

    def test_admin_settings(self, logged_in_page, tmp_path, run_core, access_token, pre_seed_stories):
        page = logged_in_page
        settings_update_url = url_for("admin_settings.settings_action", action="settings", _external=True)
        settings_form = page.locator("#settings-container form#admin-settings-form")
        tlp_select = settings_form.get_by_test_id("settings-default-tlp-level").first
        collector_proxy_input = settings_form.get_by_test_id("settings-default-collector-proxy").first
        collector_interval_input = settings_form.get_by_test_id("settings-default-collector-interval").first
        story_conflict_input = settings_form.get_by_test_id("settings-default-story-conflict-retention").first
        news_conflict_input = settings_form.get_by_test_id("settings-default-news-item-conflict-retention").first
        settings_submit = settings_form.get_by_test_id("settings-submit").first
        stories_import_url = url_for("assess.import_stories", _external=True)

        def go_to_admin_settings():
            page.goto(url_for("admin_settings.settings", _external=True))
            expect(collector_interval_input).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/docs_settings.png")

        def check_default_values():
            expect(tlp_select).to_have_attribute("required", "")
            expect(tlp_select).to_have_value("clear")
            expect(collector_proxy_input).to_be_empty()
            expect(collector_interval_input).to_have_attribute("required", "")
            expect(collector_interval_input).to_have_value("0 */8 * * *")
            expect(story_conflict_input).to_have_attribute("required", "")
            expect(story_conflict_input).to_have_value("200")
            expect(news_conflict_input).to_have_attribute("required", "")
            expect(news_conflict_input).to_have_value("200")

        def change_default_values():
            expect(collector_interval_input).to_be_visible()
            tlp_select.select_option("red")
            collector_proxy_input.fill("https://test")
            collector_interval_input.fill("0 */8 * * 1")
            story_conflict_input.fill("20")
            news_conflict_input.fill("21")
            with page.expect_response(settings_update_url) as response_info:
                settings_submit.click()
            assert response_info.value.ok, f"Expected 2xx status, but got {response_info.value.status}"
            expect(page.get_by_test_id("settings-default-tlp-level").first).to_have_value("red")

        def check_new_values():
            expect(page.get_by_role("link", name="Taranis AI Logo")).to_be_visible()

            expect(page.get_by_test_id("settings-default-tlp-level").first).to_have_value("red")
            expect(collector_proxy_input).to_have_value("https://test/")
            expect(collector_interval_input).to_have_value("0 */8 * * 1")
            expect(story_conflict_input).to_have_value("20")
            expect(news_conflict_input).to_have_value("21")

        def test_export_all_stories(story_list):
            export_btn = page.get_by_test_id("story-export-button")
            export_all_btn = page.get_by_test_id("story-export-dialog-button")
            export_dialog = page.locator("dialog[data-export-dialog]")

            # export all stories
            self.highlight_element(export_btn).click()
            expect(export_dialog).to_be_visible()
            with page.expect_download() as dl_info:
                self.highlight_element(export_all_btn).click()
            download = dl_info.value
            assert download is not None
            download_path = download.path()
            assert download_path is not None

            with open(download_path, "r", encoding="utf-8") as f:
                exported = json.load(f)

            # convert both exported stories and stories in story_list to a comparable format
            expected_stories = {
                (item["story_id"], remove_tz(item["published"]), item["id"], item["title"], item["content"]) for item in story_list
            }

            received_stories = {
                (
                    item["id"],
                    remove_tz(item["created"]),
                    item["news_items"][0]["id"],
                    item["news_items"][0]["title"],
                    item["news_items"][0]["content"],
                )
                for item in exported
            }

            assert expected_stories == received_stories, "Exported stories do not match stories in DB"

            if export_dialog.is_visible():
                page.keyboard.press("Escape")
            expect(export_dialog).not_to_be_visible()

        def test_export_stories_metadata_time_filter(story_list):
            export_btn = page.get_by_test_id("story-export-button")
            export_meta_btn = page.get_by_test_id("story-export-dialog-with-metadata-button")
            time_from_input = page.get_by_test_id("story-export-time-from")
            time_to_input = page.get_by_test_id("story-export-time-to")
            export_dialog = page.locator("dialog[data-export-dialog]")

            time_from = "2024-05-01T00:00"
            time_to = "2024-06-01T00:00"

            self.highlight_element(export_btn).click()
            expect(export_dialog).to_be_visible()
            time_from_input.fill(time_from)
            time_to_input.fill(time_to)

            # export stories with metdata between time_from and time_to
            with page.expect_download() as dl_info:
                self.highlight_element(export_meta_btn).click()

            download = dl_info.value
            assert download is not None
            download_path = download.path()
            assert download_path is not None

            # check if query params in URL
            assert "timefrom=" in download.url
            assert "timeto=" in download.url
            assert "metadata=true" in download.url

            with open(download_path, "r", encoding="utf-8") as f:
                exported = json.load(f)

            tf = datetime.fromisoformat(time_from)
            tt = datetime.fromisoformat(time_to)

            expected = {
                (
                    item["story_id"],
                    item["id"],
                    item["title"],
                    item["content"],
                    item["source"],
                    item["author"],
                    item["link"],
                    remove_tz(item["published"]),
                )
                for item in story_list
                if tf <= datetime.fromisoformat(remove_tz(item["published"])) <= tt
            }

            got = {
                (
                    story["id"],
                    ni["id"],
                    ni["title"],
                    ni["content"],
                    ni["source"],
                    ni["author"],
                    ni["link"],
                    remove_tz(story["created"]),
                )
                for story in exported
                for ni in story.get("news_items", [])
            }

            assert expected == got, "Exported stories with metadata do not match fixture stories within time filter"

            if export_dialog.is_visible():
                page.keyboard.press("Escape")
            expect(export_dialog).not_to_be_visible()

        def import_stories_from_json():
            export_response = requests.get(
                f"{run_core}/admin/export-stories",
                params={"metadata": "true"},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30,
            )
            export_response.raise_for_status()
            import_payload = export_response.json()

            imported_story_title = f"Imported Story {uuid.uuid4().hex[:8]}"
            imported_story_id = str(uuid.uuid4())
            story_to_import = import_payload[0]
            story_to_import["id"] = imported_story_id
            story_to_import["title"] = imported_story_title

            for index, news_item in enumerate(story_to_import["news_items"], start=1):
                news_item["id"] = str(uuid.uuid4())
                news_item["story_id"] = imported_story_id
                news_item["title"] = f"{imported_story_title} News {index}"
                news_item["link"] = f"https://example.com/{imported_story_id}/{index}"
                news_item.pop("hash", None)

            import_file = tmp_path / "settings_story_import.json"
            import_file.write_text(json.dumps([story_to_import]), encoding="utf-8")

            with page.expect_response(stories_import_url) as response_info:
                page.get_by_test_id("settings-story-import-file").set_input_files(str(import_file))
                page.get_by_test_id("settings-story-import-submit").click()
            assert response_info.value.ok, f"Expected 2xx status, but got {response_info.value.status}"

            page.goto(url_for("assess.assess", _external=True))
            expect(page.get_by_test_id("assess")).to_be_visible()
            page.get_by_placeholder("Search stories").fill(imported_story_title)
            page.get_by_placeholder("Search stories").press("Enter")
            imported_story = page.locator("article", has=page.get_by_test_id("story-title").filter(has_text=imported_story_title)).first
            expect(imported_story).to_be_visible()

        def revert_to_default_values():
            page.goto(url_for("admin_settings.settings", _external=True))
            tlp_select.select_option("clear")
            collector_proxy_input.fill("")
            expect(collector_interval_input).to_be_visible()
            collector_interval_input.fill("0 */8 * * *")
            story_conflict_input.fill("200")
            news_conflict_input.fill("200")
            with page.expect_response(settings_update_url) as response_info:
                settings_submit.click()
            assert response_info.value.ok, f"Expected 2xx status, but got {response_info.value.status}"

        def test_clear_cache() -> None:
            page.goto(url_for("admin_settings.settings", _external=True))
            page.get_by_role("button", name="Invalidate Cache").click()

        go_to_admin_settings()
        check_default_values()
        change_default_values()
        check_new_values()
        test_export_all_stories(pre_seed_stories)
        test_export_stories_metadata_time_filter(pre_seed_stories)
        import_stories_from_json()
        revert_to_default_values()
        test_clear_cache()

    def test_open_api(self, logged_in_page: Page):
        page = logged_in_page
        page.goto(url_for("admin.dashboard", _external=True))
        with page.expect_popup() as openapi_info:
            self.highlight_element(page.get_by_role("link", name="OpenAPI")).click()
        openapi_page = openapi_info.value
        expect(openapi_page.locator("iframe").content_frame.get_by_role("heading", name="Taranis AI 1.").first).to_be_visible()
