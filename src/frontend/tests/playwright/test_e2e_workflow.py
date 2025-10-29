#!/usr/bin/env python3
import time
import pytest
from playwright.sync_api import expect, Page

# from typing import Callable
from flask import url_for


from playwright_helpers import PlaywrightHelpers


@pytest.mark.e2e_user_workflow
class TestUserWorkflow(PlaywrightHelpers):
    def test_e2e_login(self, taranis_frontend: Page):
        page = taranis_frontend
        page.goto(url_for("base.login", _external=True))

        self.add_keystroke_overlay(page)

        expect(page).to_have_title("Taranis AI", timeout=5000)

        self.highlight_element(page.get_by_placeholder("Username"))
        page.get_by_placeholder("Username").fill("admin")
        self.highlight_element(page.get_by_placeholder("Password"))
        page.get_by_placeholder("Password").fill("admin")
        self.highlight_element(page.get_by_role("button", name="login")).click()
        page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")

    def test_assess(self, taranis_frontend: Page, stories_date_descending_not_important: list, stories_date_descending_important: list):
        #        Test definitions
        # ===============================

        def go_to_assess():
            self.highlight_element(page.get_by_role("link", name="Assess").first).click()
            page.wait_for_url("**/assess**", wait_until="domcontentloaded")
            # expect(page).to_have_title("Taranis AI | Assess")

        # def test_hotkey_menu():
        #     page.keyboard.press("Control+Shift+L")
        #     self.short_sleep(duration=1)
        #     assert_hotkey_menu()
        #     self.short_sleep(duration=2)
        #     page.keyboard.press("Escape")
        #     self.short_sleep(duration=1)

        def assert_hotkey_menu():
            expect(page.get_by_role("listbox")).to_contain_text("General")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + Shift + L")
            expect(page.get_by_role("listbox")).to_contain_text("Open the HotKeys Legend.")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + K")
            expect(page.get_by_role("listbox")).to_contain_text("Focus the Search Bar.")
            expect(page.get_by_role("listbox")).to_contain_text("Assess")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + Space")
            expect(page.get_by_role("listbox")).to_contain_text(
                "Mark all selected items as read (if all are read already, mark them as unread)."
            )
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + I")
            expect(page.get_by_role("listbox")).to_contain_text("Mark all selected items as important.")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + A")
            expect(page.get_by_role("listbox")).to_contain_text("Select all items currently loaded.")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + Shift + S")
            expect(page.get_by_role("listbox")).to_contain_text("Add selected items to last report.")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + E")
            expect(page.get_by_role("listbox")).to_contain_text("Open Edit View of Story")
            expect(page.get_by_role("listbox")).to_contain_text("Stories")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + M")
            expect(page.get_by_role("listbox")).to_contain_text("Create a new story.")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + Space")
            expect(page.get_by_role("listbox")).to_contain_text(
                "Mark all selected items as read (if all are read already, mark them as unread)."
            )
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + I")
            expect(page.get_by_role("listbox")).to_contain_text("Mark all selected items as important.")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + Shift + S")
            expect(page.get_by_role("listbox")).to_contain_text("Add open story to last report.")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + E")
            expect(page.get_by_role("listbox")).to_contain_text("Open Edit View of Story")
            expect(page.get_by_role("listbox")).to_contain_text("Reports")
            expect(page.get_by_role("listbox")).to_contain_text("Ctrl + M")
            expect(page.get_by_role("listbox")).to_contain_text("Create a new report.")

        def apply_filter():
            page.get_by_role("radio", name="Shift").check()
            page.get_by_label("Read").select_option("true")
            page.get_by_label("Read").select_option("false")
            page.get_by_label("Important").select_option("false")
            page.get_by_label("Important").select_option("true")
            page.get_by_role("link", name="Reset filters ctrl+esc").click()
            page.get_by_label("Important").select_option("true")
            expect(page.get_by_test_id("assess_story_count").get_by_text("5")).to_be_visible()
            page.get_by_role("link", name="Reset filters ctrl+esc").click()
            page.get_by_label("Read").select_option("false")
            page.get_by_label("Important").select_option("false")

        def assess_workflow_1(non_important_story_ids):
            # Check summary and mark as read
            assert len(non_important_story_ids) == 28

            # first story
            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[0]}").get_by_test_id("story-summary"), scroll=False
            )
            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[0]}").get_by_test_id("toggle-read"), scroll=False
            ).click()

            # next story
            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[1]}").get_by_test_id("story-summary"), scroll=False
            )
            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[1]}").get_by_test_id("toggle-read"), scroll=False
            ).click()

            for i in range(2, 7):
                self.highlight_element(
                    page.get_by_test_id(f"story-card-{non_important_story_ids[i]}").get_by_test_id("toggle-read"), scroll=False
                ).click()

            # select multiple, press mark as read once
            for i in range(7, 10):
                self.highlight_element(page.get_by_test_id(f"story-card-{non_important_story_ids[i]}"), scroll=False).click()
            self.highlight_element(page.get_by_role("button", name="Mark as read")).click()

            # remaining stories
            for i in range(10, 20):
                self.highlight_element(
                    page.get_by_test_id(f"story-card-{non_important_story_ids[i]}").get_by_test_id("toggle-read"), scroll=False
                ).click()

            # after all stories are marked as read in first page, last story is carried over -> mark it twice
            self.highlight_element(
                page.get_by_test_id(f"story-card-{non_important_story_ids[19]}").get_by_test_id("toggle-read"), scroll=False
            ).click()

            for i in range(20, 28):
                print(f"Marking story {non_important_story_ids[i]} as read AND is {i}/28")
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
            self.highlight_element(page.get_by_test_id("toggle-read")).click()
            # Remove mark as important
            self.highlight_element(page.get_by_test_id("toggle-important")).click()

            go_to_assess()
            page.get_by_role("link", name="Reset filters ctrl+esc").click()
            page.get_by_label("Read").select_option("false")
            page.get_by_label("Important").select_option("true")

            # Merge stories
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[2]}")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{important_story_ids[3]}")).click()
            self.highlight_element(page.get_by_role("button", name="Cluster")).click()
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

    def test_reports(self, taranis_frontend: Page):
        #        Test definitions
        # ===============================

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
            # TODO: Fix bug: Modal popup is _never_ detached from DOM, only hidden -> locator with :visible needed and after secod add to report the modal does not even disapear
            # Select all
            self.highlight_element(page.get_by_test_id("assess-select-all-button")).click()
            self.highlight_element(page.get_by_role("button", name="Add to Report")).click()

            # First dialog
            dialog = page.locator("#share_story_to_report_dialog:visible")
            self.highlight_element(dialog.get_by_label("Report Add Stories to report")).click()
            self.highlight_element(dialog.get_by_text("Test Report")).click()
            self.highlight_element(dialog.get_by_role("button", name="Share")).click()
            dialog.wait_for(state="hidden")

            # Second dialog
            self.highlight_element(page.get_by_test_id("story-title").first).click()
            self.highlight_element(page.get_by_role("button", name="Add to Report")).click()

            dialog = page.locator("#share_story_to_report_dialog:visible")
            self.highlight_element(dialog.get_by_label("Report Add Stories to report")).click()
            self.highlight_element(dialog.get_by_text("Test Disinformation Title")).click()
            self.highlight_element(dialog.get_by_role("button", name="Share")).click()
            page.keyboard.press("Escape")

        def modify_report_1():
            self.highlight_element(page.get_by_role("cell", name="Test Report")).click()
            self.highlight_element(page.get_by_placeholder("Date"), scroll=False).fill("17/3/2024")
            self.highlight_element(page.get_by_placeholder("Timeframe"), scroll=False).fill("12/2/2024 - 21/2/2024")
            self.highlight_element(page.get_by_placeholder("Handler", exact=True), scroll=False).fill("John Doe")
            self.highlight_element(page.get_by_placeholder("CO-Handler"), scroll=False).fill("Arthur Doyle")
            page.get_by_role("searchbox", name="news").click()
            news_choices = page.locator(".choices", has=page.get_by_role("searchbox", name="news"))
            news_choices.get_by_role("option").nth(0).click()
            news_choices = page.locator(".choices", has=page.get_by_role("searchbox", name="news"))
            news_choices.get_by_role("option").nth(1).click()
            page.keyboard.press("Escape")

            page.get_by_role("searchbox", name="vulnerabilities").click()

            vuln_choices = page.locator(".choices", has=page.get_by_role("searchbox", name="vulnerabilities"))
            vuln_choices.get_by_role("option").nth(2).click()
            page.get_by_role("searchbox", name="vulnerabilities").click()
            vuln_choices = page.locator(".choices", has=page.get_by_role("searchbox", name="vulnerabilities"))
            vuln_choices.get_by_role("option").nth(3).click()
            page.keyboard.press("Escape")
            page.get_by_test_id("save-report").click()
            page.get_by_role("link", name="Stacked view").click()

            page.get_by_role("link", name="Split view").click()

            page.get_by_role("button", name="Completed").click()
            # TODO: see if needed: page.get_by_test_id("save-report").click()
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

        modify_report_1()

        # TODO: tag search not implemented yet
        # go_to_assess()
        # check_reports_items_by_tag()

    def test_e2e_publish(self, taranis_frontend: Page):
        # def test_e2e_publish(self, taranis_frontend: Page, create_html_render: Callable):
        page = taranis_frontend

        self.highlight_element(page.get_by_role("link", name="Publish").first).click()
        page.wait_for_url("**/publish", wait_until="domcontentloaded")
        # expect(page).to_have_title("Taranis AI | Publish")

        self.highlight_element(page.get_by_role("button", name="New Product").first).click()
        page.get_by_label("Product Type Select an item").click()
        page.get_by_label("Product Type Select an item").select_option("5")

        page.get_by_role("textbox", name="Title").fill("Test Product Title")
        page.get_by_role("textbox", name="Description").click()
        page.get_by_role("textbox", name="Description").fill("Test Product Description")
        page.get_by_role("button", name="! Create Product").click()

        # self.short_sleep(duration=1)
        # create_html_render()

        # self.highlight_element(page.get_by_role("main").locator("header").get_by_role("button", name="Render Product")).click()
        # expect(page.get_by_test_id("text-render")).to_contain_text(
        #     "Thanks to Cybersecurity experts, the world of IT is now safe.", timeout=10_000
        # )
        page.screenshot(path="./tests/playwright/screenshots/screenshot_publish.png")
