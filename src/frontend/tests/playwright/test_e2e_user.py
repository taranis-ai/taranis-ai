#!/usr/bin/env python3
import uuid
from datetime import date

import pytest
from flask import url_for
from playwright.sync_api import Error, Page, expect
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

    def test_user_dashboard(self, logged_in_page: Page, forward_console_and_page_errors, stories_function_wrapper):
        page = logged_in_page

        def test_dashboard_edit_settings(page: Page) -> None:
            expect(page.get_by_role("link", name="Taranis AI Logo")).to_be_visible()

            page.locator("#dashboard").get_by_role("link", name="Assess").click()
            expect(page.get_by_test_id("assess_story_count")).to_contain_text("20 / 33")
            page.get_by_role("link", name="Dashboard").click()
            expect(page.get_by_role("link", name="Taranis AI Logo")).to_be_visible()

            page.locator("#dashboard").get_by_role("link", name="Analyze").click()
            expect(page.get_by_test_id("new-report-button")).to_contain_text("New Report")
            page.get_by_role("link", name="Dashboard").click()
            expect(page.get_by_role("link", name="Taranis AI Logo")).to_be_visible()

            page.locator("#dashboard").get_by_role("link", name="Publish").click()
            expect(page.get_by_test_id("new-product-button")).to_contain_text("New Product")
            page.get_by_role("link", name="Dashboard").click()
            expect(page.get_by_role("link", name="Taranis AI Logo")).to_be_visible()

            page.get_by_role("link", name="Edit Dashboard").click()
            expect(page.get_by_role("group", name="Days to look back for")).to_be_visible()

            page.get_by_role("group", name="Show Trending Clusters").get_by_label("False").uncheck()
            page.get_by_role("group", name="Show Charts in Dashboard").get_by_label("False").click()
            page.get_by_role("button", name="Update Dashboard Settings").click()
            expect(page.locator("#dashboard").get_by_text("Trending Tags (last 7 days)")).not_to_be_visible()
            expect(page.get_by_role("main")).to_be_visible()
            page.get_by_role("link", name="Edit Dashboard").click()
            expect(page.get_by_role("group", name="Days to look back for")).to_be_visible()

            page.get_by_role("group", name="Show Trending Clusters").locator("label").click()
            expect(page.get_by_role("checkbox", name="True")).to_be_visible()

            page.get_by_role("group", name="Show Charts in Dashboard").locator("label").click()
            page.get_by_role("button", name="Update Dashboard Settings").click()
            expect(page.locator("#dashboard")).to_contain_text("Trending Tags (last 7 days)")
            expect(page.locator("#dashboard")).to_contain_text("Location")

            expect(page.locator("#dashboard")).to_contain_text("Organization")
            expect(page.locator("#dashboard")).to_contain_text("Product")
            expect(page.locator("#dashboard")).to_contain_text("Person")

        def test_dashboard_entity_location_pagination(page: Page) -> None:
            page.get_by_role("link", name="Location").click()
            expect(page.locator("div").filter(has_text="plotly-logomark").nth(5)).to_be_visible()
            expect(page.locator("tbody")).to_contain_text("USA")
            expect(page.locator("tbody")).to_contain_text("6")
            expect(page.locator("tbody")).to_contain_text("Wärmestuben")
            expect(page.locator("tbody")).to_contain_text("1")
            expect(page.locator("tfoot")).to_contain_text("Page 1 of 7")
            page.get_by_text("›").click()
            expect(page.get_by_role("row", name="Page 2")).to_be_visible()
            page.get_by_text("›").click()
            expect(page.get_by_role("row", name="Page 3")).to_be_visible()
            page.get_by_text("›").click()
            expect(page.get_by_role("row", name="Page 4")).to_be_visible()
            page.get_by_text("›").click()
            expect(page.get_by_role("row", name="Page 5")).to_be_visible()
            page.get_by_text("›").click()
            expect(page.get_by_role("row", name="Page 6")).to_be_visible()
            page.get_by_text("›").click()
            expect(page.locator("tfoot")).to_contain_text("Page 7 of 7")
            expect(page.locator("tbody")).to_contain_text("Airport")
            page.get_by_text("«").click()
            expect(page.locator("tbody")).to_contain_text("USA")  # Wait for first page to load again
            page.get_by_role("combobox").click()
            page.get_by_role("combobox").select_option("5")
            cluster_table = page.get_by_test_id("cluster-table")
            all_rows = cluster_table.locator("tbody tr")
            expect(all_rows).to_have_count(5)
            expect(page.locator("tfoot")).to_contain_text("Page 1 of 26")

        def test_clear_cache(page: Page) -> None:
            page.get_by_role("link", name="Administration").click()
            expect(page.get_by_role("link", name="Taranis AI Logo")).to_be_visible()
            page.get_by_test_id("admin-menu-Settings").click()
            page.get_by_role("button", name="Invalidate Cache").click()

        page.goto(url_for("base.dashboard", _external=True))
        expect(page.locator("#dashboard")).to_be_visible()
        test_dashboard_edit_settings(page)
        test_dashboard_entity_location_pagination(page)
        test_clear_cache(page)  # TODO Fix cache (necessary because cache is not correctly invalidated)

    def test_user_profile(self, logged_in_page: Page, forward_console_and_page_errors, pre_seed_stories):
        page = logged_in_page

        def go_to_user_profile():
            page.goto(url_for("user.settings", _external=True))
            expect(page.get_by_text("User", exact=True)).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/user_profile.png")

        def check_profile():
            expect(page.locator("#user-settings-form")).to_contain_text("Split view")
            expect(page.locator("#user-settings-form")).to_contain_text("Show charts")
            expect(page.locator("#user-settings-form")).to_contain_text("Infinite scroll")
            expect(page.locator("#user-settings-form")).to_contain_text("Compact view")
            expect(page.locator("#user-settings-form")).to_contain_text("Dark theme")
            expect(page.locator("#user-settings-form")).to_contain_text("Advanced story edit options")
            expect(page.locator("#user-settings-form")).to_contain_text("Language")
            expect(page.locator("#user-settings-form")).to_contain_text("End of shift")
            page.locator(".collapse > input").check()
            expect(page.locator("#user-password-form")).to_contain_text("Current password")
            expect(page.locator("#user-password-form")).to_contain_text("New password")
            expect(page.locator("#user-password-form")).to_contain_text("Confirm new password")
            expect(page.get_by_role("button", name="Update password")).to_be_visible()

        def change_password_fail():
            # Wrong current password
            page.get_by_role("textbox", name="Current password").fill("admin1")
            page.get_by_role("textbox", name="New password", exact=True).fill("admin")
            page.get_by_role("textbox", name="Confirm new password").fill("admin")
            page.get_by_role("button", name="Update password").click()
            expect(page.locator("#notification-bar")).to_contain_text("Old password is incorrect")

            # Mismatching new passwords
            page.get_by_role("textbox", name="Current password").fill("admin")
            page.get_by_role("textbox", name="New password", exact=True).fill("admin1")
            page.get_by_role("textbox", name="Confirm new password").fill("admin")
            page.get_by_role("button", name="Update password").click()
            expect(page.locator("#notification-bar")).to_contain_text("New password and confirm password do not match")

        def change_password():
            page.get_by_role("textbox", name="Current password").fill("admin")
            page.get_by_role("textbox", name="New password", exact=True).fill("admin1")
            page.get_by_role("textbox", name="Confirm new password").fill("admin1")
            page.get_by_role("button", name="Update password").click()
            expect(page.locator("#notification-bar")).to_contain_text("Password changed successfully")

        def test_user_profile_settings_adjustments():
            page.get_by_role("checkbox", name="Infinite scroll Automatically").uncheck()
            page.get_by_role("checkbox", name="Compact view Use condensed").check()
            page.get_by_role("button", name="Save changes").click()
            page.get_by_role("link", name="Assess").click()

            page.get_by_role("link", name="Next").click()

            page.get_by_role("checkbox", name="Compact view").uncheck()

            page.get_by_role("list").get_by_role("button").click()
            expect(page.get_by_role("link", name="Profile")).to_be_visible()

            page.get_by_role("link", name="User Settings").click()
            page.get_by_role("checkbox", name="Infinite scroll Automatically").check()
            page.get_by_role("checkbox", name="Compact view Use condensed").uncheck()
            page.get_by_role("button", name="Save changes").click()

        def relog_in():
            page.get_by_role("list").get_by_role("button").click()
            expect(page.get_by_role("link", name="Profile")).to_be_visible()

            page.get_by_role("link", name="Logout").click()
            expect(page.get_by_role("img", name="Taranis Logo")).to_be_visible()

            page.get_by_role("textbox", name="Username").fill("admin")
            page.get_by_role("textbox", name="Username").press("Tab")
            page.get_by_role("textbox", name="Password").fill("admin1")
            page.get_by_test_id("login-button").click()
            expect(page.get_by_role("link", name="Taranis AI Logo")).to_be_visible()

        def change_password_back():
            page.get_by_role("list").get_by_role("button").click()
            expect(page.get_by_role("link", name="Profile")).to_be_visible()

            page.get_by_role("link", name="User Settings").click()
            expect(page.get_by_role("link", name="Taranis AI Logo")).to_be_visible()

            page.locator(".collapse > input").check()
            page.get_by_role("textbox", name="Current password").fill("admin1")
            page.get_by_role("textbox", name="New password", exact=True).fill("admin")
            page.get_by_role("textbox", name="New password", exact=True).press("Tab")
            page.get_by_role("textbox", name="Confirm new password").fill("admin")
            page.get_by_role("button", name="Update password").click()
            expect(page.locator("#notification-bar")).to_contain_text("Password changed successfully")

        go_to_user_profile()
        check_profile()
        change_password_fail()
        change_password()
        test_user_profile_settings_adjustments()
        relog_in()
        change_password_back()

    def test_user_assess(self, logged_in_page: Page, forward_console_and_page_errors, pre_seed_stories):
        page = logged_in_page
        # page.set_default_timeout(0)

        def go_to_assess():
            page.goto(url_for("assess.assess", _external=True))

            expect(page.get_by_test_id("assess_story_count")).to_contain_text("20 / 57", timeout=30000)

            expect(page.get_by_test_id("assess")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/user_assess.png")

        def access_story():
            story_articles = page.locator("#story-list article")
            expect(story_articles.first).to_be_visible()
            story = story_articles.nth(0)
            menu = story.get_by_test_id("story-actions-menu")
            expect(menu).to_be_attached()
            expect(menu).to_be_visible()
            expect(menu).to_be_enabled()
            title = story.locator("h2[data-testid='story-title']").inner_text()

            story.get_by_test_id("toggle-summary").click()
            story.get_by_test_id("story-actions-menu").click()
            story.get_by_test_id("toggle-read").click()
            story.get_by_test_id("story-actions-menu").click()
            story.get_by_test_id("toggle-important").click()
            story.get_by_test_id("story-actions-menu").click()
            story.get_by_test_id("share-story").click()
            page.get_by_role("button", name="✕").click()
            story.get_by_test_id("open-detail-view").click()
            expect(page.get_by_test_id("story-title")).to_contain_text(title)
            page.get_by_test_id("edit-story").click()
            page.get_by_role("textbox", name="Title").fill(f"{title} edited title")
            page.get_by_role("textbox", name="Summary").fill("Test summary")
            page.get_by_role("textbox", name="Analyst comments").fill("Test analyst comment")
            page.get_by_test_id("tag-name-input").fill("tag name")
            page.get_by_test_id("tag-value-input").fill("tag value")
            page.get_by_role("button", name="Add attribute").click()
            page.get_by_test_id("attribute-key-input").nth(1).fill("attr")
            page.get_by_test_id("attribute-value-input").nth(1).fill("value attr")
            page.get_by_role("button", name="Add tag").click()
            page.get_by_test_id("tag-name-input").nth(1).fill("tag 2")
            page.get_by_test_id("tag-value-input").nth(1).fill("value2")
            page.get_by_role("button", name="Save changes").click()
            page.get_by_role("link", name="Advanced view").click()
            expect(page.get_by_role("complementary")).to_contain_text("Story status")
            page.get_by_text("Cybersecurity · Not Classified").click()
            expect(page.get_by_role("complementary")).to_contain_text("Cybersecurity · Not Classified")
            expect(page.get_by_role("complementary")).to_contain_text("AI assisted actions")
            expect(page.get_by_role("complementary")).to_contain_text("Generate AI summary")
            expect(page.get_by_role("complementary")).to_contain_text("Run sentiment analysis")
            expect(page.get_by_role("complementary")).to_contain_text("Cybersecurity classification")
            page.get_by_role("link", name="Return to story").click()
            expect(page.get_by_test_id("story-title")).to_contain_text("Pharmaceutical Trade Secrets Theft by APT76 edited title")

        def infinite_scroll_all_items():
            page.goto(url_for("assess.assess", _external=True))

            expect(page.get_by_test_id("assess")).to_be_visible()

            expect(page.get_by_test_id("assess_story_count")).to_contain_text("20 / 57 Stories")
            page.mouse.wheel(0, 5500)
            expect(page.get_by_test_id("assess_story_count")).to_contain_text("40 / 57 Stories")
            page.mouse.wheel(0, 5500)
            expect(page.get_by_test_id("assess_story_count")).to_contain_text("57 / 57 Stories")
            page.mouse.wheel(0, 5500)
            expect(page.get_by_text("You're all caught up.")).to_be_visible()

            expect(page.get_by_test_id("assess_story_selection_count")).to_be_hidden()
            page.get_by_role("button", name="Select all").click()
            expect(page.get_by_test_id("assess_story_selection_count")).to_contain_text("57 stories selected")
            page.get_by_role("button", name="Clear selection Esc").click()
            expect(page.get_by_test_id("assess_story_selection_count")).to_be_hidden()

        def group_stories():
            page.goto(url_for("assess.assess", _external=True))
            expect(page.get_by_role("radiogroup", name="Time presets")).to_be_visible()
            main_story_title = page.get_by_test_id("story-title").nth(0).inner_text()
            page.get_by_test_id("story-title").nth(0).click()
            page.get_by_test_id("story-title").nth(1).click()
            page.get_by_test_id("story-title").nth(2).click()
            page.get_by_test_id("story-title").nth(3).click()

            page.get_by_role("button", name="Cluster").click()
            page.get_by_test_id("dialog-story-cluster-open").click()
            expect(page.get_by_test_id("story-title")).to_contain_text(main_story_title)
            page.get_by_role("heading", name=main_story_title, exact=True).click()
            expect(page.get_by_role("heading", name="Search & Scope")).not_to_be_visible()
            expect(page.get_by_text("Filter", exact=True)).not_to_be_visible()

        go_to_assess()
        access_story()
        infinite_scroll_all_items()
        group_stories()

    def test_user_analyze(
        self,
        logged_in_page: Page,
        forward_console_and_page_errors,
        pre_seed_report_stories,
        pre_seed_report_type_all_attribute_types_optional,
        pre_seed_report_type_all_attribute_types_required,
    ):
        page = logged_in_page
        report_story_one, report_story_two = pre_seed_report_stories
        story_search_term = " ".join(report_story_one["title"].split()[:2])
        story_search_term_lower = story_search_term.lower()
        report_story_two_primary_link = report_story_two["news_items"][0]["link"]
        report_uuid = ""

        def go_to_analyze():
            page.goto(url_for("analyze.analyze", _external=True))
            expect(page.get_by_test_id("analyze")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/user_analyze.png")

        def check_report_view_layout_changes():
            page.get_by_test_id("new-report-button").click()
            expect(page.get_by_role("heading", name="Create Report")).to_be_visible()

            page.get_by_role("textbox", name="Title").fill("test title")
            page.get_by_label("Report Type Select a report").select_option("4")
            page.get_by_role("link", name="Stacked view").click()
            expect(page.get_by_role("textbox", name="Title")).to_have_value("test title")
            expect(page.get_by_label("Report Type CERT Report")).to_have_value("4")
            page.get_by_role("link", name="Split view").click()
            expect(page.get_by_role("textbox", name="Title")).to_have_value("test title")
            expect(page.get_by_label("Report Type CERT Report")).to_have_value("4")
            page.get_by_test_id("save-report").click()
            expect(page.get_by_test_id("report-new-product")).to_be_visible()
            expect(page.get_by_role("button", name="Completed")).to_be_visible()
            expect(page.get_by_role("button", name="Incomplete")).to_be_visible()
            expect(page.get_by_placeholder("Date")).to_be_visible()
            expect(page.get_by_placeholder("Timeframe")).to_be_visible()
            expect(page.get_by_placeholder("Handler", exact=True)).to_be_visible()
            expect(page.get_by_placeholder("CO-Handler")).to_be_visible()
            expect(page.get_by_role("searchbox", name="news")).to_be_visible()
            expect(page.get_by_role("searchbox", name="vulnerabilities")).to_be_visible()
            page.get_by_placeholder("Date").fill("today")
            page.get_by_placeholder("Timeframe").fill("last week")
            page.get_by_placeholder("Handler", exact=True).fill("me")
            page.get_by_placeholder("CO-Handler").fill("you")
            page.get_by_test_id("save-report").click()
            page.get_by_placeholder("Date").fill("yesterday")
            page.get_by_role("link", name="Stacked view").click()
            expect(page.get_by_placeholder("Date")).to_have_value("yesterday")
            page.get_by_role("link", name="Split view").click()
            expect(page.get_by_placeholder("Date")).to_have_value("yesterday")
            expect(page.get_by_test_id("report-new-product")).to_be_visible()
            expect(page.get_by_role("button", name="Completed")).to_be_visible()
            expect(page.get_by_role("button", name="Incomplete")).to_be_visible()

        def delete_test_report():
            report_uuid = page.get_by_test_id("report-id").inner_text().split("ID: ")[1]
            page.get_by_role("link", name="Analyze").click()
            page.get_by_test_id(f"action-delete-{report_uuid}").click()
            expect(page.get_by_role("dialog", name="Are you sure you want to")).to_be_visible()
            page.get_by_role("button", name="OK").click()

        def create_report():
            new_report_button = page.get_by_role("button", name="New Report")
            expect(new_report_button).to_be_visible()
            new_report_button.click()
            page.get_by_role("textbox", name="Title").fill("Test report")
            page.get_by_label("Report Type Select a report").select_option("4")
            expect(page.locator("#report_form")).to_contain_text("Attributes will be generated after the report item has been created.")
            expect(page.get_by_test_id("analyze").locator("section")).to_contain_text("No stories assigned to this report.")
            page.get_by_test_id("save-report").click()
            notification = page.locator("#notification-bar [role='alert']")
            if notification.is_visible():
                notification.click()
                expect(notification).to_be_hidden()
            page.get_by_placeholder("Date").fill("1.1.2000")
            page.get_by_placeholder("Timeframe").fill("January")
            page.get_by_placeholder("Handler", exact=True).fill("Kluger")
            page.get_by_placeholder("CO-Handler").fill("Mensch")
            page.get_by_test_id("save-report").click()
            report_uuid = page.get_by_test_id("report-id").inner_text().split("ID: ")[1]
            assert self.is_uuid4(report_uuid), f"Expected a valid UUID4, got {report_uuid}"
            return report_uuid

        def add_stories_to_report():
            page.goto(url_for("assess.assess", _external=True))

            page.get_by_role("searchbox", name="Select sources").click()

            page.get_by_placeholder("Search stories").fill(story_search_term)
            page.get_by_placeholder("Search stories").press("Enter")

            page.get_by_role("heading", name=report_story_one["title"]).click()
            page.get_by_role("heading", name=report_story_two["title"]).click()
            page.get_by_role("button", name="Add to Report").click()
            popup = page.get_by_label("Add Stories to report")
            popup.click()
            popup.get_by_text("Test report").click()
            page.locator("#share_story_to_report_dialog").get_by_role("button", name="Share").click()
            expect(page.get_by_text("In Reports").nth(1)).to_be_visible()
            expect(page.get_by_text("In Reports").nth(2)).to_be_visible()

        def verify_report_actions(report_uuid: str):
            def test_report_item_view():
                page.get_by_role("link", name="Analyze").click()
                page.get_by_role("link", name="Test report").click()
                expect(page.get_by_role("paragraph")).to_contain_text("test summary")

            def test_remove_story_from_report():
                page.get_by_role("link", name="Analyze").click()
                page.get_by_role("link", name="Test report").click()
                page.get_by_test_id(f"remove-story-{report_story_one['id']}").click()

            def test_story_in_report_assess_view():
                page.get_by_role("link", name="Assess").click()
                page.get_by_placeholder("Search stories").fill(story_search_term_lower)
                page.get_by_placeholder("Search stories").press("Enter")
                expect(page.get_by_test_id("assess").get_by_text("In Reports")).to_be_visible()  # only one should be in a report now

            def test_create_product_from_report():
                page.get_by_role("link", name="Analyze").click()
                page.get_by_test_id(f"action-edit-{report_uuid}").click()
                page.get_by_test_id("report-new-product").click()
                expect(page.get_by_role("heading", name="Create Product")).to_be_visible()
                expect(page.get_by_text("Create Product").first).to_be_visible()

            def test_clone_and_delete_report():
                page.get_by_role("link", name="Analyze").click()
                page.get_by_test_id(f"action-clone-report-{report_uuid}").click()
                cloned_report = page.get_by_role("link", name=f"Test Report ({date.today().isoformat()}", exact=False)
                assert cloned_report is not None
                clone_report_href = cloned_report.get_attribute("href")
                assert clone_report_href is not None
                cloned_report_uuid = clone_report_href.split("/")[-1]
                assert self.is_uuid4(cloned_report_uuid), f"Expected a valid UUID4, got {cloned_report_uuid}"
                page.get_by_test_id(f"action-delete-{cloned_report_uuid}").click()
                page.get_by_role("button", name="OK").click()
                page.get_by_role("link", name="Test report").click()
                expect(page.get_by_test_id("report-stories").get_by_role("link", name=report_story_two["title"])).to_be_visible()
                expect(page.get_by_test_id(f"story-link-{report_story_two['id']}")).to_contain_text(report_story_two_primary_link)
                report_uuid_2 = page.get_by_test_id("report-id").inner_text().split("ID: ")[1]
                return report_uuid_2

            def cleanup_reports(report_uuid_2: str):
                page.get_by_role("link", name="Analyze").click()
                page.get_by_test_id(f"action-delete-{report_uuid_2}").click()
                page.get_by_role("button", name="OK").click()

            test_report_item_view()
            test_remove_story_from_report()
            test_story_in_report_assess_view()
            test_create_product_from_report()
            report_uuid_2 = test_clone_and_delete_report()
            cleanup_reports(report_uuid_2)

        def check_various_report_type_fields():
            def create_new_report():
                page.get_by_test_id("new-report-button").click()
                expect(page.get_by_role("heading", name="Create Report")).to_be_visible()
                page.get_by_role("textbox", name="Title").fill("all attr report")
                page.get_by_label("Report Type Select a report").select_option("6")
                page.get_by_test_id("save-report").click()
                page.get_by_text("Report item created").click()

                expect(page.get_by_role("searchbox", name="Related Story")).to_be_visible()
                expect(page.get_by_placeholder("STRING field")).to_be_visible()
                expect(page.get_by_placeholder("NUMBER field")).to_be_visible()
                expect(page.get_by_role("group", name="Boolean")).to_be_visible()
                expect(page.get_by_role("group", name="Confidentiality (Radio)")).to_be_visible()
                expect(page.get_by_text("Impact (Enum)")).to_be_visible()
                expect(page.get_by_role("heading", name="Narrative and Timing")).to_be_visible()
                expect(page.get_by_placeholder("TEXT field", exact=True)).to_be_visible()
                expect(page.get_by_placeholder("RICH_TEXT field")).to_be_visible()
                expect(page.get_by_role("textbox", name="Date", exact=True)).to_be_visible()
                expect(page.get_by_role("textbox", name="Time", exact=True)).to_be_visible()
                expect(page.get_by_role("textbox", name="Date Time")).to_be_visible()
                expect(page.get_by_label("TLP Level Clear Green Amber")).to_be_visible()
                expect(page.get_by_role("heading", name="Technical References and")).to_be_visible()
                expect(page.get_by_text('Unsupported attribute type "')).to_be_visible()
                expect(page.get_by_text("Attachment editing is not yet")).to_be_visible()
                expect(page.get_by_label("CPE Select an option")).to_be_visible()
                expect(page.get_by_placeholder("CVE field")).to_be_visible()
                expect(page.get_by_placeholder("CVSS field")).to_be_visible()
                page.get_by_test_id("save-report").click()
                page.get_by_text("Report item updated").click()

            def add_stories_to_new_report():
                page.get_by_role("link", name="Assess").click()
                page.get_by_placeholder("Search stories").fill(story_search_term)
                page.get_by_placeholder("Search stories").press("Enter")
                page.get_by_role("heading", name=report_story_one["title"]).click()
                page.get_by_role("heading", name=report_story_two["title"]).click()
                expect(page.get_by_role("button", name="Cluster")).to_be_visible()

                page.get_by_role("button", name="Add to Report").click()
                popup = page.get_by_label("Add Stories to report")
                popup.click()
                popup.get_by_text("all attr report").click()
                page.locator("#share_story_to_report_dialog").get_by_role("button", name="Share").click()

            def set_report_fields():
                page.get_by_role("link", name="Analyze").click()
                expect(page.get_by_role("row", name="all attr report")).to_be_visible()

                page.get_by_role("link", name="all attr report").click()
                page.locator(".choices__inner").click()
                page.get_by_role("option", name="Report Story 1 Add Story").click()
                expect(page.get_by_role("option", name="Report Story 1 Remove item:")).to_be_visible()

                page.locator("div").filter(has_text="Title * Report Type CERT").nth(3).click()
                page.get_by_placeholder("STRING field").click()
                page.get_by_placeholder("STRING field").fill("string")
                page.get_by_placeholder("NUMBER field").click()
                page.get_by_placeholder("NUMBER field").fill("111")
                expect(page.locator("#attribute-4")).to_be_visible()
                page.locator("#attribute-4").check()
                page.get_by_role("radio", name="UNRESTRICTED").check()
                page.get_by_label("Impact (Enum) Select an").select_option("Malicious code execution affecting CIA of the system")
                page.get_by_placeholder("TEXT field", exact=True).click()
                page.get_by_placeholder("TEXT field", exact=True).fill("text")
                page.get_by_placeholder("RICH_TEXT field").click()
                page.get_by_placeholder("RICH_TEXT field").fill("rich text")
                page.get_by_role("textbox", name="Date", exact=True).fill("2026-02-05")
                page.get_by_role("textbox", name="Time", exact=True).fill("111111-11-11")
                page.get_by_role("textbox", name="Date Time").fill("111111-11-11")
                page.get_by_label("TLP Level Clear Green Amber").select_option("red")
                page.locator("div").filter(has_text="Stories Remove all Report").nth(4).click()
                page.get_by_placeholder("CVE field").fill("CVE-2026-24888")
                page.get_by_placeholder("CVSS field").fill("1")
                page.get_by_test_id("save-report").click()

            def empty_report_fields():
                page.get_by_text("Report item updated").click()
                page.get_by_role("option", name="Report Story 1 Remove item:").get_by_role("button").click()
                page.get_by_placeholder("STRING field").fill("")
                page.get_by_placeholder("NUMBER field").click()
                page.get_by_placeholder("NUMBER field").fill("")
                expect(page.locator("#attribute-4")).to_be_visible()

                page.locator("#attribute-4").uncheck()
                page.get_by_role("radio", name="CLASSIFIED").check()
                page.get_by_label("Impact (Enum) Malicious code").select_option("Privilege escalation")
                page.get_by_placeholder("TEXT field", exact=True).fill("")
                page.get_by_placeholder("RICH_TEXT field").fill("")
                page.get_by_role("textbox", name="Date", exact=True).fill("")
                page.get_by_role("textbox", name="Time", exact=True).fill("")
                page.get_by_role("textbox", name="Date Time").fill("")
                page.get_by_label("TLP Level Clear Green Amber").select_option("clear")
                page.get_by_placeholder("CVE field").fill("")
                page.get_by_placeholder("CVSS field").fill("")
                page.get_by_test_id("save-report").click()
                page.get_by_text("Report item updated").click()

            def check_report_fields():
                page.get_by_role("link", name="Analyze").click()
                expect(page.get_by_role("row", name="all attr report")).to_be_visible()

                page.get_by_role("link", name="all attr report").click()
                expect(page.get_by_role("textbox", name="Title")).to_have_value("all attr report")
                expect(page.get_by_role("option", name="Report Story 1 Remove item:")).not_to_be_visible()
                expect(page.get_by_placeholder("STRING field")).to_be_empty()
                expect(page.get_by_placeholder("NUMBER field")).to_be_empty()
                expect(page.locator("#attribute-4")).not_to_be_checked()
                expect(page.get_by_role("radio", name="CLASSIFIED")).to_be_checked()
                expect(page.get_by_role("radio", name="UNRESTRICTED")).not_to_be_checked()
                expect(page.get_by_label("Impact (Enum) Malicious code")).to_have_value("Privilege escalation")
                expect(page.get_by_placeholder("TEXT field", exact=True)).to_be_empty()
                expect(page.get_by_placeholder("RICH_TEXT field")).to_be_empty()
                expect(page.get_by_role("textbox", name="Date", exact=True)).to_be_empty()
                expect(page.get_by_role("textbox", name="Time", exact=True)).to_be_empty()
                expect(page.get_by_role("textbox", name="Date Time")).to_be_empty()
                expect(page.get_by_label("TLP Level Clear Green Amber")).to_have_value("clear")
                expect(page.get_by_placeholder("CVE field")).to_be_empty()
                expect(page.get_by_placeholder("CVSS field")).to_be_empty()
                expect(page.locator("#report_form")).to_contain_text("Use the NVD CVSS calculator to determine the score.")
                page.get_by_test_id("save-report").click()
                page.get_by_text("Report item updated").click()

            def check_invalid_states():
                with pytest.raises(Error, match=r"Cannot type text"):
                    page.get_by_placeholder("NUMBER field").fill("aaa")
                page.get_by_placeholder("CVE field").fill("111")

                page.get_by_test_id("save-report").click()
                expect(page.get_by_text("Report item updated")).not_to_be_visible()
                page.get_by_placeholder("CVE field").fill("")

                page.get_by_placeholder("CVSS field").fill("a")
                page.get_by_test_id("save-report").click()
                expect(page.get_by_text("Report item updated")).not_to_be_visible()
                page.get_by_placeholder("CVSS field").fill("")
                with pytest.raises(Error, match=r"Malformed value"):
                    page.get_by_role("textbox", name="Date", exact=True).fill("xxxx-xx-xx")
                    page.get_by_test_id("save-report").click()
                    expect(page.get_by_text("Report item updated")).not_to_be_visible()

                    page.get_by_role("textbox", name="Time", exact=True).fill("xxxx-xx-xx")
                    page.get_by_test_id("save-report").click()
                    expect(page.get_by_text("Report item updated")).not_to_be_visible()

                    page.get_by_role("textbox", name="Date Time").fill("xxxx-xx-xx")
                    page.get_by_test_id("save-report").click()
                    expect(page.get_by_text("Report item updated")).not_to_be_visible()

            def delete_new_report():
                report_uuid = page.get_by_test_id("report-id").inner_text().split("ID: ")[1]
                page.get_by_role("link", name="Analyze").click()
                expect(page.get_by_role("row", name="all attr report")).to_be_visible()
                page.get_by_test_id(f"action-delete-{report_uuid}").click()
                expect(page.get_by_role("dialog", name="Are you sure you want to")).to_be_visible()
                page.get_by_role("button", name="OK").click()
                page.get_by_text("Successfully deleted report").click()

            def create_new_report_required():
                page.get_by_test_id("new-report-button").click()
                expect(page.get_by_role("heading", name="Create Report")).to_be_visible()
                page.get_by_role("textbox", name="Title").fill("all attr report REQUIRED")
                page.get_by_label("Report Type Select a report").select_option("7")
                page.get_by_test_id("save-report").click()
                page.get_by_text("Report item created").click()
                page.pause()
                expect(page.get_by_role("searchbox", name="Related Story")).to_be_visible()
                expect(page.get_by_placeholder("STRING field*")).to_be_visible()
                expect(page.get_by_placeholder("NUMBER field*")).to_be_visible()
                expect(page.get_by_role("group", name="Boolean*")).to_be_visible()
                expect(page.get_by_role("group", name="Confidentiality (Radio)*")).to_be_visible()
                expect(page.get_by_text("Impact (Enum)*")).to_be_visible()
                expect(page.get_by_role("heading", name="Narrative and Timing*")).to_be_visible()
                expect(page.get_by_placeholder("TEXT field*", exact=True)).to_be_visible()
                expect(page.get_by_placeholder("RICH_TEXT field*")).to_be_visible()
                expect(page.get_by_role("textbox", name="Date*", exact=True)).to_be_visible()
                expect(page.get_by_role("textbox", name="Time*", exact=True)).to_be_visible()
                expect(page.get_by_role("textbox", name="Date Time*")).to_be_visible()
                expect(page.get_by_label("TLP Level* Clear Green Amber")).to_be_visible()
                expect(page.get_by_role("heading", name="Technical References and")).to_be_visible()
                expect(page.get_by_text('Unsupported attribute type "')).to_be_visible()
                expect(page.get_by_text("Attachment editing is not yet")).to_be_visible()
                expect(page.get_by_label("CPE Select an option")).to_be_visible()
                expect(page.get_by_placeholder("CVE field*", exact=True)).to_be_visible()
                expect(page.get_by_placeholder("CVSS field*", exact=True)).to_be_visible()
                page.get_by_test_id("save-report").click()
                page.get_by_text("Report item updated").click()

            def add_stories_to_new_report_required():
                page.get_by_role("link", name="Assess").click()
                page.get_by_placeholder("Search stories").fill(story_search_term)
                page.get_by_placeholder("Search stories").press("Enter")
                page.get_by_role("heading", name=report_story_one["title"]).click()
                page.get_by_role("heading", name=report_story_two["title"]).click()
                expect(page.get_by_role("button", name="Cluster")).to_be_visible()

                page.get_by_role("button", name="Add to Report").click()
                popup = page.get_by_label("Add Stories to report")
                popup.click()
                popup.get_by_text("all attr report").click()
                page.locator("#share_story_to_report_dialog").get_by_role("button", name="Share").click()

            def set_report_fields_required():
                page.get_by_role("link", name="Analyze").click()
                expect(page.get_by_role("row", name="all attr report")).to_be_visible()

                page.get_by_role("link", name="all attr report").click()
                page.locator(".choices__inner").click()
                page.get_by_role("option", name="Report Story 1 Add Story").click()
                expect(page.get_by_role("option", name="Report Story 1 Remove item:")).to_be_visible()

                page.locator("div").filter(has_text="Title * Report Type CERT").nth(3).click()
                page.get_by_placeholder("STRING field").click()
                page.get_by_placeholder("STRING field").fill("string")
                page.get_by_placeholder("NUMBER field").click()
                page.get_by_placeholder("NUMBER field").fill("111")
                expect(page.locator("#attribute-4")).to_be_visible()
                page.locator("#attribute-4").check()
                page.get_by_role("radio", name="UNRESTRICTED").check()
                page.get_by_label("Impact (Enum) Select an").select_option("Malicious code execution affecting CIA of the system")
                page.get_by_placeholder("TEXT field", exact=True).click()
                page.get_by_placeholder("TEXT field", exact=True).fill("text")
                page.get_by_placeholder("RICH_TEXT field").click()
                page.get_by_placeholder("RICH_TEXT field").fill("rich text")
                page.get_by_role("textbox", name="Date", exact=True).fill("2026-02-05")
                page.get_by_role("textbox", name="Time", exact=True).fill("111111-11-11")
                page.get_by_role("textbox", name="Date Time").fill("111111-11-11")
                page.get_by_label("TLP Level Clear Green Amber").select_option("red")
                page.locator("div").filter(has_text="Stories Remove all Report").nth(4).click()
                page.get_by_placeholder("CVE field").fill("CVE-2026-24888")
                page.get_by_placeholder("CVSS field").fill("1")
                page.get_by_test_id("save-report").click()

            def empty_report_fields_required():
                page.get_by_text("Report item updated").click()
                page.get_by_role("option", name="Report Story 1 Remove item:").get_by_role("button").click()
                page.get_by_placeholder("STRING field").fill("")
                page.get_by_placeholder("NUMBER field").click()
                page.get_by_placeholder("NUMBER field").fill("")
                expect(page.locator("#attribute-4")).to_be_visible()

                page.locator("#attribute-4").uncheck()
                page.get_by_role("radio", name="CLASSIFIED").check()
                page.get_by_label("Impact (Enum) Malicious code").select_option("Privilege escalation")
                page.get_by_placeholder("TEXT field", exact=True).fill("")
                page.get_by_placeholder("RICH_TEXT field").fill("")
                page.get_by_role("textbox", name="Date", exact=True).fill("")
                page.get_by_role("textbox", name="Time", exact=True).fill("")
                page.get_by_role("textbox", name="Date Time").fill("")
                page.get_by_label("TLP Level Clear Green Amber").select_option("clear")
                page.get_by_placeholder("CVE field").fill("")
                page.get_by_placeholder("CVSS field").fill("")
                page.get_by_test_id("save-report").click()
                page.pause()
                page.get_by_text("Report item updated").click()

            def check_report_fields_required():
                page.get_by_role("link", name="Analyze").click()
                expect(page.get_by_role("row", name="all attr report")).to_be_visible()

                page.get_by_role("link", name="all attr report").click()
                expect(page.get_by_role("textbox", name="Title")).to_have_value("all attr report REQUIRED")
                expect(page.get_by_role("option", name="Report Story 1 Remove item:")).not_to_be_visible()
                expect(page.get_by_placeholder("STRING field*")).to_be_empty()
                expect(page.get_by_placeholder("NUMBER field*")).to_be_empty()
                expect(page.locator("#attribute-4")).not_to_be_checked()
                expect(page.get_by_role("radio", name="CLASSIFIED")).to_be_checked()
                expect(page.get_by_role("radio", name="UNRESTRICTED")).not_to_be_checked()
                expect(page.get_by_label("Impact (Enum) Malicious code")).to_have_value("Privilege escalation")
                expect(page.get_by_placeholder("TEXT field*", exact=True)).to_be_empty()
                expect(page.get_by_placeholder("RICH_TEXT field*")).to_be_empty()
                expect(page.get_by_role("textbox", name="Date*", exact=True)).to_be_empty()
                expect(page.get_by_role("textbox", name="Time*", exact=True)).to_be_empty()
                expect(page.get_by_role("textbox", name="Date Time*")).to_be_empty()
                expect(page.get_by_label("TLP Level* Clear Green Amber")).to_have_value("clear")
                expect(page.get_by_placeholder("CVE field*")).to_be_empty()
                expect(page.get_by_placeholder("CVSS field*")).to_be_empty()
                expect(page.locator("#report_form")).to_contain_text("Use the NVD CVSS calculator to determine the score.")
                page.get_by_test_id("save-report").click()
                page.get_by_text("Report item updated").click()

            def check_invalid_states_required():
                with pytest.raises(Error, match=r"Cannot type text"):
                    page.get_by_placeholder("NUMBER field").fill("aaa")
                page.get_by_placeholder("CVE field").fill("111")

                page.get_by_test_id("save-report").click()
                expect(page.get_by_text("Report item updated")).not_to_be_visible()
                page.get_by_placeholder("CVE field").fill("")

                page.get_by_placeholder("CVSS field").fill("a")
                page.get_by_test_id("save-report").click()
                expect(page.get_by_text("Report item updated")).not_to_be_visible()
                page.get_by_placeholder("CVSS field").fill("")
                with pytest.raises(Error, match=r"Malformed value"):
                    page.get_by_role("textbox", name="Date", exact=True).fill("xxxx-xx-xx")
                    page.get_by_test_id("save-report").click()
                    expect(page.get_by_text("Report item updated")).not_to_be_visible()

                    page.get_by_role("textbox", name="Time", exact=True).fill("xxxx-xx-xx")
                    page.get_by_test_id("save-report").click()
                    expect(page.get_by_text("Report item updated")).not_to_be_visible()

                    page.get_by_role("textbox", name="Date Time").fill("xxxx-xx-xx")
                    page.get_by_test_id("save-report").click()
                    expect(page.get_by_text("Report item updated")).not_to_be_visible()

            def delete_new_report_required():
                report_uuid = page.get_by_test_id("report-id").inner_text().split("ID: ")[1]
                page.get_by_role("link", name="Analyze").click()
                expect(page.get_by_role("row", name="all attr report")).to_be_visible()
                page.get_by_test_id(f"action-delete-{report_uuid}").click()
                expect(page.get_by_role("dialog", name="Are you sure you want to")).to_be_visible()
                page.get_by_role("button", name="OK").click()
                page.get_by_text("Successfully deleted report").click()

            create_new_report()
            add_stories_to_new_report()
            set_report_fields()
            empty_report_fields()
            check_report_fields()
            check_invalid_states()
            delete_new_report()
            ####
            create_new_report_required()
            add_stories_to_new_report_required()
            set_report_fields_required()
            empty_report_fields_required()
            check_report_fields_required()
            check_invalid_states_required()
            delete_new_report_required()

        go_to_analyze()
        check_report_view_layout_changes()
        delete_test_report()
        go_to_analyze()
        report_uuid = create_report()
        add_stories_to_report()
        verify_report_actions(report_uuid)
        go_to_analyze()
        check_various_report_type_fields()

    def test_publish(self, logged_in_page: Page, forward_console_and_page_errors, stories_session_wrapper):
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
