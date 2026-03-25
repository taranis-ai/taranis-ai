#!/usr/bin/env python3
import re

import pytest

# from typing import Callable
from flask import url_for
from playwright.sync_api import Page, expect
from playwright_helpers import PlaywrightHelpers


@pytest.mark.usefixtures("e2e_ci")
@pytest.mark.e2e_user_workflow
class TestUserWorkflow(PlaywrightHelpers):
    def test_e2e_login(self, taranis_frontend: Page):
        page = taranis_frontend
        # page.set_default_timeout(0)
        page.goto(url_for("base.login", _external=True))

        self.add_keystroke_overlay(page)

        expect(page).to_have_title("Taranis AI", timeout=5000)

        self.highlight_element(page.get_by_placeholder("Username"))
        page.get_by_placeholder("Username").fill("admin")
        self.highlight_element(page.get_by_placeholder("Password"))
        page.get_by_placeholder("Password").fill("admin")
        self.highlight_element(page.get_by_role("button", name="login")).click()
        page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")
        expect(page.locator("#dashboard")).to_contain_text("Assess")
        expect(page.locator("#dashboard")).to_contain_text("Analyze")
        expect(page.locator("#dashboard")).to_contain_text("Publish")
        expect(page.locator("#dashboard")).to_contain_text("Connectors")

    def test_instance_setup(self, logged_in_page: Page):
        page = logged_in_page

        page.goto(url_for("assess.assess", _external=True))
        expect(page.get_by_test_id("assess")).to_be_visible()

        page.goto(url_for("admin.osint_sources", _external=True))
        load_defaults_button = page.get_by_role("button", name="Load default OSINT Source")
        if load_defaults_button.is_visible():
            self.highlight_element(load_defaults_button).click()

        osint_table = page.get_by_test_id("osint_source-table")
        all_rows = osint_table.locator("tbody tr")
        expect(all_rows.first).to_be_visible()
        assert all_rows.count() >= 1

    def test_assess(self, logged_in_page: Page, stories_date_descending_not_important: list, stories_date_descending_important: list):
        page = logged_in_page
        expected_important_count = len(stories_date_descending_important)

        def go_to_assess():
            page.goto(url_for("assess.assess", _external=True))
            page.wait_for_url("**/assess**", wait_until="domcontentloaded")
            expect(page.get_by_test_id("assess")).to_be_visible()

        def apply_filter():
            self.highlight_element(page.get_by_role("radio", name="Shift")).check()
            self.highlight_element(page.get_by_label("Read")).select_option("true")
            self.highlight_element(page.get_by_label("Read")).select_option("false")
            self.highlight_element(page.get_by_label("Important")).select_option("false")
            self.highlight_element(page.get_by_label("Important")).select_option("true")
            self.highlight_element(page.get_by_role("link", name="Reset filters ctrl+esc")).click()
            self.highlight_element(page.get_by_label("Important")).select_option("true")
            expect(page.get_by_test_id("assess_story_count")).to_contain_text(str(expected_important_count))
            self.highlight_element(page.get_by_role("link", name="Reset filters ctrl+esc")).click()
            self.highlight_element(page.get_by_label("Read")).select_option("false")
            self.highlight_element(page.get_by_label("Important")).select_option("false")

        def mark_story_as_read(story_id: str):
            story_card = page.get_by_test_id(f"story-card-{story_id}")
            self.highlight_element(story_card.get_by_test_id("story-actions-menu")).click()
            toggle_read = story_card.get_by_test_id("toggle-read")
            expect(toggle_read).to_be_visible()
            self.highlight_element(toggle_read, scroll=False).click()
            expect(story_card.get_by_test_id("story-summary")).to_be_visible()

        def assess_workflow_1(non_important_story_ids):
            assert len(non_important_story_ids) >= 4, "Expected at least four non-important stories for the workflow test"

            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[0]}").get_by_test_id("story-summary"), scroll=False
            )
            expect(page.get_by_test_id(f"story-card-{non_important_story_ids[0]}").get_by_test_id("story-summary")).to_be_visible()
            mark_story_as_read(non_important_story_ids[0])

            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[1]}").get_by_test_id("story-summary"), scroll=False
            )
            expect(page.get_by_test_id(f"story-card-{non_important_story_ids[1]}").get_by_test_id("story-summary")).to_be_visible()
            mark_story_as_read(non_important_story_ids[1])

            for story_id in non_important_story_ids[2:4]:
                self.highlight_element(page.get_by_test_id(f"story-card-{story_id}").get_by_test_id("story-actions-menu")).click()
                self.highlight_element(page.get_by_test_id(f"story-card-{story_id}"), scroll=False).click()
            self.highlight_element(page.get_by_role("button", name="Mark as read")).click()
            expect(page.get_by_test_id("assess_story_selection_count")).to_be_hidden()

        def assess_workflow_2(important_story_ids):
            assert len(important_story_ids) >= 4, "Expected at least four important stories for the workflow test"
            page.get_by_label("Important").select_option("true")

            for story_id in important_story_ids[:4]:
                self.highlight_element(page.get_by_test_id(f"story-card-{story_id}").get_by_test_id("toggle-summary")).click()
                self.highlight_element(page.get_by_test_id(f"story-card-{story_id}").get_by_test_id("toggle-summary")).click()

            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[0]}").get_by_test_id("toggle-summary")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[0]}").get_by_test_id("open-detail-view")).click()
            self.short_sleep(0.5)

            self.highlight_element(page.get_by_test_id("story-actions-menu")).click()
            self.highlight_element(page.get_by_test_id("toggle-read")).click()
            self.highlight_element(page.get_by_test_id("story-actions-menu")).click()
            self.highlight_element(page.get_by_test_id("toggle-important")).click()

            go_to_assess()
            page.get_by_role("link", name="Reset filters ctrl+esc").click()
            page.get_by_label("Read").select_option("false")
            page.get_by_label("Important").select_option("true")

            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[2]}")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[3]}")).click()
            self.highlight_element(page.get_by_role("button", name="Cluster")).click()
            expect(page.get_by_test_id("story-to-merge")).to_have_count(2)
            page.get_by_test_id("dialog-story-cluster-submit").click()

            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[1]}").get_by_test_id("edit-story")).click()
            self.highlight_element(page.get_by_role("textbox", name="Summary")).fill(
                "Recent cyber activities highlight significant threats from various Advanced Persistent Threat (APT) groups. APT67 has been conducting espionage operations targeting the global mining industry, while APT55 has been injecting malicious code into widely used applications by attacking software development firms. Additionally, APT56 has been involved in cross-border hacking operations affecting government websites. Meanwhile, APT65 has led a malware campaign that leaked sensitive data from several legal firms. These incidents underscore the persistent and diverse nature of cyber threats posed by these groups across industries and regions."
            )
            self.highlight_element(page.get_by_role("textbox", name="Analyst comments")).fill("I like this story, it needs to be reviewed.")
            page.get_by_role("button", name="Add tag").click()
            page.get_by_test_id("tag-name-input").last.fill("Austria")
            page.get_by_test_id("tag-value-input").last.fill("Location")
            page.get_by_role("button", name="Save changes").click()
            page.get_by_role("button", name="Add attribute").click()
            page.get_by_test_id("attribute-key-input").last.fill("Analyst_1")
            page.get_by_test_id("attribute-value-input").last.fill("read")
            page.get_by_role("button", name="Save changes").click()

            go_to_assess()

        go_to_assess()
        apply_filter()
        assess_workflow_1(stories_date_descending_not_important)
        assess_workflow_2(stories_date_descending_important)

    def test_reports(self, logged_in_page: Page, stories_date_descending: list):
        page = logged_in_page
        report_title = "Test Report"
        disinformation_title = "Test Disinformation Title"

        def go_to_analyze():
            page.goto(url_for("analyze.analyze", _external=True))
            page.wait_for_url("**/analyze", wait_until="domcontentloaded")
            expect(page.get_by_test_id("analyze")).to_be_visible()

        def go_to_assess():
            page.goto(url_for("assess.assess", _external=True))
            page.wait_for_url("**/assess**", wait_until="domcontentloaded")
            expect(page.get_by_test_id("assess")).to_be_visible()

        def create_report(report_type: str, title: str) -> str:
            self.highlight_element(page.get_by_role("button", name="New Report").first).click()
            page.get_by_label("Select a report").select_option(report_type)
            self.highlight_element(page.get_by_label("Title")).fill(title)
            if title == report_title:
                page.screenshot(path="./tests/playwright/screenshots/report_item_add.png")
            self.highlight_element(page.get_by_role("button", name="Create Report")).click()
            expect(page.get_by_test_id("report-id")).to_have_text(re.compile(r"^ID: [0-9a-f-]{36}$"))
            return page.get_by_test_id("report-id").inner_text().split("ID: ")[1]

        def add_stories_to_reports():
            story_titles = page.get_by_test_id("story-title")
            expect(story_titles.first).to_be_visible()
            self.highlight_element(story_titles.first).click()
            if story_titles.count() > 1:
                self.highlight_element(story_titles.nth(1)).click()
            self.highlight_element(page.get_by_role("button", name="Add to Report")).click()
            self.highlight_element(page.get_by_test_id("select-report-input")).click()
            self.highlight_element(page.get_by_text(report_title)).click()
            self.highlight_element(page.get_by_test_id("share-to-report-dialog-button")).click()

            self.highlight_element(page.get_by_test_id("story-title").first).click()
            self.highlight_element(page.get_by_role("button", name="Add to Report")).click()
            self.highlight_element(page.get_by_test_id("select-report-input")).click()
            self.highlight_element(page.get_by_text(disinformation_title)).click()
            self.highlight_element(page.get_by_test_id("share-to-report-dialog-button")).click()
            page.keyboard.press("Escape")

        def select_first_options(searchbox_name: str, limit: int = 2):
            self.highlight_element(page.get_by_role("searchbox", name=searchbox_name)).click()
            choices = page.locator(".choices", has=page.get_by_role("searchbox", name=searchbox_name))
            option_count = choices.get_by_role("option").count()
            for index in range(min(limit, option_count)):
                self.highlight_element(choices.get_by_role("option").nth(index)).click()
                choices = page.locator(".choices", has=page.get_by_role("searchbox", name=searchbox_name))
            page.keyboard.press("Escape")

        def modify_report(report_id: str):
            page.goto(url_for("analyze.report", report_id=report_id, _external=True))
            first_story_link = page.locator("[data-testid^='story-link-']").first
            expect(first_story_link).to_be_visible()
            self.highlight_element(page.get_by_placeholder("Date"), scroll=False).fill("17/3/2024")
            self.highlight_element(page.get_by_placeholder("Timeframe"), scroll=False).fill("12/2/2024 - 21/2/2024")
            self.highlight_element(page.get_by_placeholder("Handler", exact=True), scroll=False).fill("John Doe")
            self.highlight_element(page.get_by_placeholder("CO-Handler"), scroll=False).fill("Arthur Doyle")
            select_first_options("news")
            select_first_options("vulnerabilities")
            self.highlight_element(page.get_by_test_id("save-report")).click()
            expect(first_story_link).to_be_visible()
            self.highlight_element(page.get_by_role("link", name="Stacked view")).click()
            expect(first_story_link).to_be_visible()
            self.highlight_element(page.get_by_role("link", name="Split view")).click()
            expect(first_story_link).to_be_visible()
            self.highlight_element(page.get_by_role("button", name="Completed")).click()
            expect(first_story_link).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/report_item_view.png")

        go_to_analyze()
        report_1_id = create_report("CERT Report", report_title)
        go_to_analyze()
        create_report("Disinformation", disinformation_title)
        go_to_assess()
        add_stories_to_reports()
        modify_report(report_1_id)

    def test_e2e_publish(self, logged_in_page: Page):
        page = logged_in_page

        page.goto(url_for("publish.publish", _external=True))
        page.wait_for_url("**/publish", wait_until="domcontentloaded")
        expect(page.get_by_test_id("product-table")).to_be_visible()

        self.highlight_element(page.get_by_role("button", name="New Product").first).click()
        product_type_select = page.get_by_label("Product Type * Select an item")
        product_type_options = product_type_select.locator("option").evaluate_all(
            """options => options
            .filter(option => option.value)
            .map(option => ({ value: option.value, label: option.textContent?.trim() ?? "" }))"""
        )
        assert product_type_options, "No product type options available for workflow publish test"
        self.highlight_element(product_type_select).select_option(product_type_options[0]["value"])

        self.highlight_element(page.get_by_role("textbox", name="Title")).fill("Test Product Title")
        self.highlight_element(page.get_by_role("textbox", name="Description")).click()
        self.highlight_element(page.get_by_role("textbox", name="Description")).fill("Test Product Description")
        self.highlight_element(page.get_by_role("button", name="! Create Product")).click()

        # Assert the existing Product
        expect(page.locator("#product_type_id option:checked")).not_to_have_value("")
        expect(page.get_by_role("textbox", name="Title")).to_be_visible()
        expect(page.get_by_role("textbox", name="Description")).to_be_visible()
        expect(page.get_by_role("cell", name="Test Report")).to_be_visible()
        expect(page.get_by_role("heading", name="No Report selected")).to_be_visible()
        expect(page.get_by_text("Please select at least one")).to_be_visible()
        expect(page.get_by_role("button", name="Render")).to_be_visible()
        expect(page.get_by_test_id("save-product")).to_be_visible()
        expect(page.get_by_text("Render Product first, to")).to_be_visible()
        expect(page.get_by_role("button", name="Update Product - Test Product")).to_be_visible()

        # self.short_sleep(duration=1)
        # create_html_render()

        # self.highlight_element(page.get_by_role("main").locator("header").get_by_role("button", name="Render Product")).click()
        # expect(page.get_by_test_id("text-render")).to_contain_text(
        #     "Thanks to Cybersecurity experts, the world of IT is now safe.", timeout=10_000
        # )
        page.screenshot(path="./tests/playwright/screenshots/screenshot_publish.png")
