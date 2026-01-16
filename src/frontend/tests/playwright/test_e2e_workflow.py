#!/usr/bin/env python3
import time

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

    def test_instance_setup(self, taranis_frontend: Page):
        page = taranis_frontend
        self.highlight_element(page.get_by_role("link", name="Assess").first).click()
        self.highlight_element(page.get_by_role("heading", name="No stories found."))
        self.highlight_element(page.get_by_role("link", name="Administration")).click()
        self.highlight_element(page.get_by_test_id("admin-menu-OSINT Source")).click()
        self.highlight_element(page.get_by_role("button", name="Load default OSINT Source")).click()
        page.wait_for_selector("tbody tr")
        rows = page.locator("tbody tr").count()
        assert rows == 10

    def test_assess(self, taranis_frontend: Page, stories_date_descending_not_important: list, stories_date_descending_important: list):
        def go_to_assess():
            self.highlight_element(page.get_by_role("link", name="Assess").first).click()
            page.wait_for_url("**/assess**", wait_until="domcontentloaded")

        def apply_filter():
            self.highlight_element(page.get_by_role("radio", name="Shift")).check()
            self.highlight_element(page.get_by_label("Read")).select_option("true")
            self.highlight_element(page.get_by_label("Read")).select_option("false")
            self.highlight_element(page.get_by_label("Important")).select_option("false")
            self.highlight_element(page.get_by_label("Important")).select_option("true")
            self.highlight_element(page.get_by_role("link", name="Reset filters ctrl+esc")).click()
            self.highlight_element(page.get_by_label("Important")).select_option("true")
            expect(page.get_by_test_id("assess_story_count").get_by_text("5")).to_be_visible()
            self.highlight_element(page.get_by_role("link", name="Reset filters ctrl+esc")).click()
            self.highlight_element(page.get_by_label("Read")).select_option("false")
            self.highlight_element(page.get_by_label("Important")).select_option("false")

        def assess_workflow_1(non_important_story_ids):
            # Check summary and mark as read
            assert len(non_important_story_ids) == 28

            # first story
            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[0]}").get_by_test_id("story-summary"), scroll=False
            )
            expect(page.get_by_test_id(f"story-card-{non_important_story_ids[0]}").get_by_test_id("story-summary")).to_be_visible()
            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[0]}").get_by_test_id("story-actions-menu")
            ).click()
            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[0]}").get_by_test_id("toggle-read"), scroll=False
            ).click()
            expect(page.get_by_test_id(f"story-card-{non_important_story_ids[0]}").get_by_test_id("story-summary")).to_be_visible()

            # next story
            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[1]}").get_by_test_id("story-summary"), scroll=False
            )
            expect(page.get_by_test_id(f"story-card-{non_important_story_ids[1]}").get_by_test_id("story-summary")).to_be_visible()
            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[1]}").get_by_test_id("story-actions-menu")
            ).click()

            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[1]}").get_by_test_id("toggle-read"), scroll=False
            ).click()
            expect(page.get_by_test_id(f"story-card-{non_important_story_ids[1]}").get_by_test_id("story-summary")).to_be_visible()

            for i in range(2, 7):
                self.highlight_element(
                    page.get_by_test_id(f"story-card-{non_important_story_ids[i]}").get_by_test_id("story-actions-menu")
                ).click()
                self.highlight_element(
                    page.get_by_test_id(f"story-card-{non_important_story_ids[i]}").get_by_test_id("toggle-read"), scroll=False
                ).click()
                expect(page.get_by_test_id(f"story-card-{non_important_story_ids[i]}").get_by_test_id("story-summary")).to_be_visible()

            # select multiple, press mark as read once
            for i in range(7, 10):
                self.highlight_element(
                    page.get_by_test_id(f"story-card-{non_important_story_ids[i]}").get_by_test_id("story-actions-menu")
                ).click()
                self.highlight_element(page.get_by_test_id(f"story-card-{non_important_story_ids[i]}"), scroll=False).click()
            self.highlight_element(page.get_by_role("button", name="Mark as read")).click()

            # remaining stories
            for i in range(10, 20):
                self.highlight_element(
                    page.get_by_test_id(f"story-card-{non_important_story_ids[i]}").get_by_test_id("story-actions-menu")
                ).click()
                self.highlight_element(
                    page.get_by_test_id(f"story-card-{non_important_story_ids[i]}").get_by_test_id("toggle-read"), scroll=False
                ).click()
                expect(page.get_by_test_id(f"story-card-{non_important_story_ids[i]}").get_by_test_id("story-summary")).to_be_visible()

            # after all stories are marked as read in first page, last story is carried over -> mark it twice
            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[19]}").get_by_test_id("story-actions-menu")
            ).click()
            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[19]}").get_by_test_id("toggle-read"), scroll=False
            ).click()

            for i in range(20, 28):
                print(f"Marking story {non_important_story_ids[i]} as read AND is {i}/28")
                self.highlight_element(
                    page.get_by_test_id(f"story-card-{non_important_story_ids[i]}").get_by_test_id("story-actions-menu")
                ).click()
                self.highlight_element(
                    page.get_by_test_id(f"story-card-{non_important_story_ids[i]}").get_by_test_id("toggle-read"), scroll=False
                ).click()

        def assess_workflow_2(important_story_ids):
            page.get_by_label("Important").select_option("true")

            # Show/unshow details of all stories
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[0]}").get_by_test_id("toggle-summary")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[0]}").get_by_test_id("toggle-summary")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[1]}").get_by_test_id("toggle-summary")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[1]}").get_by_test_id("toggle-summary")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[2]}").get_by_test_id("toggle-summary")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[2]}").get_by_test_id("toggle-summary")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[3]}").get_by_test_id("toggle-summary")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[3]}").get_by_test_id("toggle-summary")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[4]}").get_by_test_id("toggle-summary")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[4]}").get_by_test_id("toggle-summary")).click()

            # Open specific story
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[0]}").get_by_test_id("toggle-summary")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[0]}").get_by_test_id("open-detail-view")).click()
            self.short_sleep(0.5)

            # Mark as read
            self.highlight_element(page.get_by_test_id("story-actions-menu")).click()
            self.highlight_element(page.get_by_test_id("toggle-read")).click()
            # Remove mark as important
            self.highlight_element(page.get_by_test_id("story-actions-menu")).click()
            self.highlight_element(page.get_by_test_id("toggle-important")).click()

            go_to_assess()
            page.get_by_role("link", name="Reset filters ctrl+esc").click()
            page.get_by_label("Read").select_option("false")
            page.get_by_label("Important").select_option("true")

            # Merge stories
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[2]}")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[3]}")).click()
            self.highlight_element(page.get_by_role("button", name="Cluster")).click()
            expect(page.get_by_test_id("story-to-merge")).to_have_count(2)
            self.expect_list_of_test_ids_visible(
                page,
                [
                    f"story-card-{important_story_ids[2]}",
                    f"story-card-{important_story_ids[3]}",
                ],
            )
            page.get_by_test_id("dialog-story-cluster-submit").click()

            # Edit story
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[4]}").get_by_test_id("edit-story")).click()

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

        #           Run test
        # ============================

        page = taranis_frontend

        go_to_assess()
        # test_hotkey_menu()
        apply_filter()
        assess_workflow_1(stories_date_descending_not_important)
        assess_workflow_2(stories_date_descending_important)

    def test_reports(self, taranis_frontend: Page, stories_date_descending: list):
        def go_to_analyze():
            self.highlight_element(page.get_by_role("link", name="Analyze").first).click()
            page.wait_for_url("**/analyze", wait_until="domcontentloaded")
            # expect(page).to_have_title("Taranis AI | Analyze")

        def go_to_assess():
            self.highlight_element(page.get_by_role("link", name="Assess").first).click()
            page.wait_for_url("**/assess**", wait_until="domcontentloaded")
            # expect(page).to_have_title("Taranis AI | Assess")

        def report_1():
            self.highlight_element(page.get_by_role("button", name="New Report").first).click()
            # page.wait_for_url("**/report/", wait_until="domcontentloaded")
            page.get_by_label("Select a report").select_option("CERT Report")

            time.sleep(0.5)
            page.screenshot(path="./tests/playwright/screenshots/report_item_add.png")

            # self.highlight_element(page.get_by_text("CERT Report")).click()
            self.highlight_element(page.get_by_label("Title")).fill("Test Report")
            self.highlight_element(page.get_by_role("button", name="Create Report")).click()

        def report_2():
            self.highlight_element(page.get_by_role("button", name="New Report")).click()
            # self.highlight_element(page.get_by_role("combobox")).click()
            # self.highlight_element(page.get_by_text("Disinformation")).click()
            page.get_by_label("Select a report").select_option("Disinformation")

            self.highlight_element(page.get_by_label("Title")).fill("Test Disinformation Title")
            self.highlight_element(page.get_by_role("button", name="Create Report")).click()

        def add_stories_to_report_1():
            # Select all
            self.highlight_element(page.get_by_test_id("assess-select-all-button")).click()
            self.highlight_element(page.get_by_role("button", name="Add to Report")).click()

            # First dialog
            self.highlight_element(page.get_by_test_id("select-report-input")).click()
            self.highlight_element(page.get_by_text("Test Report")).click()
            self.highlight_element(page.get_by_test_id("share-to-report-dialog-button")).click()

            # Second dialog
            self.highlight_element(page.get_by_test_id("story-title").first).click()
            self.highlight_element(page.get_by_role("button", name="Add to Report")).click()

            self.highlight_element(page.get_by_test_id("select-report-input")).click()
            self.highlight_element(page.get_by_text("Test Disinformation Title")).click()
            self.highlight_element(page.get_by_test_id("share-to-report-dialog-button")).click()
            page.keyboard.press("Escape")

        def modify_report_1(stories_date_descending):
            self.highlight_element(page.get_by_role("cell", name="Test Report")).click()
            self.expect_list_of_test_ids_visible(page, [f"story-link-{story_id}" for story_id in stories_date_descending])
            self.highlight_element(page.get_by_placeholder("Date"), scroll=False).fill("17/3/2024")
            self.highlight_element(page.get_by_placeholder("Timeframe"), scroll=False).fill("12/2/2024 - 21/2/2024")
            self.highlight_element(page.get_by_placeholder("Handler", exact=True), scroll=False).fill("John Doe")
            self.highlight_element(page.get_by_placeholder("CO-Handler"), scroll=False).fill("Arthur Doyle")

            # NEWS dropdown
            self.highlight_element(page.get_by_role("searchbox", name="news")).click()
            news_choices = page.locator(".choices", has=page.get_by_role("searchbox", name="news"))
            self.highlight_element(news_choices.get_by_role("option").nth(0)).click()
            news_choices = page.locator(".choices", has=page.get_by_role("searchbox", name="news"))
            self.highlight_element(news_choices.get_by_role("option").nth(1)).click()
            page.keyboard.press("Escape")

            # VULNERABILITIES dropdown
            self.highlight_element(page.get_by_role("searchbox", name="vulnerabilities")).click()
            vuln_choices = page.locator(".choices", has=page.get_by_role("searchbox", name="vulnerabilities"))
            self.highlight_element(vuln_choices.get_by_role("option").nth(2)).click()

            self.highlight_element(page.get_by_role("searchbox", name="vulnerabilities")).click()
            vuln_choices = page.locator(".choices", has=page.get_by_role("searchbox", name="vulnerabilities"))
            self.highlight_element(vuln_choices.get_by_role("option").nth(3)).click()
            page.keyboard.press("Escape")

            # Save & toggle report views
            self.highlight_element(page.get_by_test_id("save-report")).click()
            self.expect_list_of_test_ids_visible(page, [f"story-link-{story_id}" for story_id in stories_date_descending])

            self.highlight_element(page.get_by_role("link", name="Stacked view")).click()
            self.expect_list_of_test_ids_visible(page, [f"story-link-{story_id}" for story_id in stories_date_descending])

            self.highlight_element(page.get_by_role("link", name="Split view")).click()
            self.expect_list_of_test_ids_visible(page, [f"story-link-{story_id}" for story_id in stories_date_descending])

            self.highlight_element(page.get_by_role("button", name="Completed")).click()
            self.expect_list_of_test_ids_visible(page, [f"story-link-{story_id}" for story_id in stories_date_descending])

            # TODO: see if needed:
            # page.get_by_test_id("save-report").click()
            time.sleep(1)
            page.screenshot(path="./tests/playwright/screenshots/report_item_view.png")

        def check_reports_items_by_tag():
            self.highlight_element(page.get_by_role("button", name="reset filter")).click()
            self.highlight_element(page.get_by_label("Tags", exact=True)).click()
            self.highlight_element(page.get_by_label("Tags", exact=True)).fill("test")
            self.short_sleep(0.5)
            self.highlight_element(page.get_by_text("Test Report").last).click()
            page.get_by_test_id("all-stories-div").click()
            page.keyboard.press("Control+A")
            self.short_sleep(duration=1)
            page.keyboard.press("Control+Space")
            self.short_sleep(duration=1)

        #           Run test
        # ============================

        page = taranis_frontend

        go_to_analyze()
        report_1()
        go_to_analyze()
        report_2()
        go_to_analyze()
        expect(page.get_by_text("Test Report")).to_be_visible()
        expect(page.get_by_text("Test Disinformation Title")).to_be_visible()

        self.highlight_element(page.get_by_role("link", name="Assess")).click()
        add_stories_to_report_1()

        go_to_analyze()

        modify_report_1(stories_date_descending)

        # TODO: tag search not implemented yet
        # go_to_assess()
        # check_reports_items_by_tag()

    def test_e2e_publish(self, taranis_frontend: Page):
        page = taranis_frontend

        self.highlight_element(page.get_by_role("link", name="Publish").first).click()
        page.wait_for_url("**/publish", wait_until="domcontentloaded")
        # expect(page).to_have_title("Taranis AI | Publish")

        self.highlight_element(page.get_by_role("button", name="New Product").first).click()
        self.highlight_element(page.get_by_label("Product Type Select an item")).click()
        page.get_by_label("Product Type Select an item").select_option("5")

        self.highlight_element(page.get_by_role("textbox", name="Title")).fill("Test Product Title")
        self.highlight_element(page.get_by_role("textbox", name="Description")).click()
        self.highlight_element(page.get_by_role("textbox", name="Description")).fill("Test Product Description")
        self.highlight_element(page.get_by_role("button", name="! Create Product")).click()

        # Assert the existing Product
        expect(page.locator("#product_type_id option:checked")).to_have_text("CERT Daily Report")
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
