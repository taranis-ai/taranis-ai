#!/usr/bin/env python3
import re
import time
import pytest
from playwright.sync_api import expect, Page

from playwright_helpers import PlaywrightHelpers


@pytest.mark.e2e_user_workflow
class TestUserWorkflow(PlaywrightHelpers):
    def test_e2e_login(self, taranis_frontend: Page):
        page = taranis_frontend
        self.add_keystroke_overlay(page)

        expect(page).to_have_title("Taranis AI", timeout=5000)

        self.highlight_element(page.get_by_placeholder("Username"))
        page.get_by_placeholder("Username").fill("admin")
        self.highlight_element(page.get_by_placeholder("Password"))
        page.get_by_placeholder("Password").fill("admin")
        self.highlight_element(page.locator("role=button")).click()
        page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")

    def test_assess(self, taranis_frontend: Page):
        def enter_hotkey_menu():
            page.keyboard.press("Control+Shift+L")
            self.short_sleep(duration=1)
            assert_hotkey_menu()
            self.short_sleep(duration=2)
            page.keyboard.press("Escape")
            self.short_sleep(duration=1)

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

        def go_to_assess():
            self.highlight_element(page.get_by_role("link", name="Assess").first).click()
            page.wait_for_url("**/assess**", wait_until="domcontentloaded")
            expect(page).to_have_title("Taranis AI | Assess")

        def apply_filter():
            # Set time filter
            self.highlight_element(
                page.locator("div").filter(has_text=re.compile(r"^Filter more details TagsTags$")).get_by_role("button").first
            ).click()
            self.highlight_element(page.get_by_role("button", name="read")).click()
            self.highlight_element(page.get_by_role("button", name="read")).click()
            expect(page.get_by_role("button", name="not read")).to_be_visible()
            self.highlight_element(page.get_by_role("button", name="important")).click()
            self.highlight_element(page.get_by_role("button", name="important")).click()
            expect(page.get_by_role("button", name="not important")).to_be_visible()

        def assess_workflow_1():
            # Check summary and mark as read
            self.highlight_element(
                page.locator("xpath=/html/body/div[1]/div/div/main/div/div/div[1]/div[2]/div/div[1]/div/div[2]/span/span"), scroll=False
            )
            self.highlight_element(
                page.locator("xpath=//*[@id='app']/div/div/main/div/div/div[1]/div[2]/div/div[2]/div/button[3]/span[3]/i"), scroll=False
            ).click()
            self.highlight_element(page.locator("xpath=/html/body/div[1]/div/div/main/div/div/div[1]/div[2]/div/div[1]/div/div[2]/span/span"))
            self.highlight_element(
                page.locator("xpath=//*[@id='app']/div/div/main/div/div/div[1]/div[2]/div/div[2]/div/button[3]/span[3]/i"), scroll=False
            ).click()

            for _ in range(1, 6):
                page.locator("xpath=/html/body/div[1]/div/div/main/div/div/div[1]/div[2]/div/div[1]/div/div[2]/span/span")

                self.highlight_element(
                    page.locator("xpath=//*[@id='app']/div/div/main/div/div/div[1]/div[2]/div/div[2]/div/button[3]/span[3]/i"), scroll=False
                ).click()

            for i in range(1, 4):
                self.highlight_element(
                    page.locator(f"xpath=/html/body/div[1]/div/div/main/div/div/div[{i}]/div[2]/div/div[1]/div/div[2]/span/span")
                ).click()

            self.highlight_element(page.get_by_role("button", name="mark as read")).click()

            for _ in range(1, 20):
                page.locator("xpath=//*[@id='app']/div/div/main/div/div/div[1]/div[2]/div/div[2]/div/button[3]/span[3]/i").click()

        def assess_workflow_2():
            self.highlight_element(page.get_by_role("button", name="not important")).click()
            self.highlight_element(page.get_by_role("button", name="important")).click()
            expect(page.get_by_role("button", name="important")).to_be_visible()

            # Check stories
            self.highlight_element(page.locator(".ml-auto > button").first).click()
            self.highlight_element(page.locator(".ml-auto > button").first).click()
            self.highlight_element(
                page.locator("div:nth-child(2) > .v-container > div > div:nth-child(2) > .ml-auto > button").first, scroll=True
            ).click()
            self.highlight_element(
                page.locator("div:nth-child(2) > .v-container > div > div:nth-child(2) > .ml-auto > button").first, scroll=True
            ).click()
            self.highlight_element(
                page.locator("div:nth-child(3) > .v-container > div > div:nth-child(2) > .ml-auto > button").first, scroll=True
            ).click()
            self.highlight_element(
                page.locator("div:nth-child(3) > .v-container > div > div:nth-child(2) > .ml-auto > button").first, scroll=True
            ).click()
            self.highlight_element(
                page.locator("div:nth-child(4) > .v-container > div > div:nth-child(2) > .ml-auto > button").first, scroll=True
            ).click()
            self.highlight_element(
                page.locator("div:nth-child(4) > .v-container > div > div:nth-child(2) > .ml-auto > button").first, scroll=True
            ).click()
            self.highlight_element(
                page.locator("div:nth-child(5) > .v-container > div > div:nth-child(2) > .ml-auto > button").first, scroll=True
            ).click()
            self.highlight_element(
                page.locator("div:nth-child(5) > .v-container > div > div:nth-child(2) > .ml-auto > button").first, scroll=True
            ).click()

            # Open story
            self.highlight_element(
                page.locator("div").filter(has_text="Patient Data Harvesting by APT60").nth(5).get_by_role("button").nth(0)
            ).click()
            self.highlight_element(
                page.locator("div").filter(has_text="Patient Data Harvesting by APT60").nth(5).get_by_role("link").nth(2)
            ).click()
            # Mark as read
            self.highlight_element(
                page.locator("div").filter(has_text="Patient Data Harvesting by APT60").nth(5).get_by_role("button").nth(3)
            ).click()
            # Remove mark as important
            self.highlight_element(
                page.locator("div").filter(has_text="Patient Data Harvesting by APT60").nth(5).get_by_role("button").nth(4)
            ).click()
            go_to_assess()
            self.highlight_element(page.get_by_role("button", name="reset filter")).click()
            self.highlight_element(page.get_by_role("button", name="read")).click()
            self.highlight_element(page.get_by_role("button", name="read")).click()
            self.highlight_element(page.get_by_role("button", name="important")).click()

            # Merge stories
            self.highlight_element(page.locator("div").filter(has_text="Advanced Phishing Techniques by APT58").nth(5)).click()
            self.highlight_element(page.locator("div").filter(has_text="APT73 Exploits Global Shipping").nth(5)).click()
            self.highlight_element(page.get_by_role("button", name="merge")).click()
            # Edit story
            self.highlight_element(
                page.locator("div").filter(has_text="Global Mining Espionage by APT67").nth(5).get_by_role("button").nth(3)
            ).click()
            self.highlight_element(page.get_by_role("listbox").get_by_role("link").nth(0)).click()
            self.highlight_element(
                page.locator("#form div").filter(has_text="Summary91›Enter your summary").get_by_role("textbox"), scroll=False
            ).fill(
                "Recent cyber activities highlight significant threats from various Advanced Persistent Threat (APT) groups. APT67 has been conducting espionage operations targeting the global mining industry, while APT55 has been injecting malicious code into widely used applications by attacking software development firms. Additionally, APT56 has been involved in cross-border hacking operations affecting government websites. Meanwhile, APT65 has led a malware campaign that leaked sensitive data from several legal firms. These incidents underscore the persistent and diverse nature of cyber threats posed by these groups across industries and regions."
            )
            self.highlight_element(
                page.locator("#form div").filter(has_text="Comment91›Enter your comment").get_by_role("textbox"), scroll=False
            ).fill("I like this story, it needs to be reviewed.")
            self.highlight_element(page.get_by_label("Tags", exact=True)).click()
            self.highlight_element(page.get_by_label("Tags", exact=True)).fill("APT75")
            self.short_sleep(0.5)
            page.get_by_label("Tags", exact=True).press("Enter")
            self.highlight_element(page.get_by_label("Tags", exact=True)).fill("APT74")
            self.short_sleep(0.5)
            page.get_by_label("Tags", exact=True).press("Enter")
            self.highlight_element(page.get_by_label("Tags", exact=True)).fill("APT76")
            self.short_sleep(0.5)
            page.get_by_label("Tags", exact=True).press("Enter")
            page.get_by_label("Tags", exact=True).fill("APT")
            page.get_by_label("Tags", exact=True).click()
            page.get_by_label("Tags", exact=True).fill("APT77")
            page.get_by_label("Tags", exact=True).press("Enter")
            page.get_by_label("Tags", exact=True).fill("APT78")
            page.get_by_label("Tags", exact=True).press("Enter")
            page.get_by_label("Tags", exact=True).fill("APT79")
            page.get_by_label("Tags", exact=True).press("Enter")
            page.get_by_label("Tags", exact=True).fill("APT80")
            page.get_by_label("Tags", exact=True).press("Enter")
            page.get_by_label("Tags", exact=True).fill("APT81")
            page.get_by_label("Tags", exact=True).press("Enter")
            self.highlight_element(page.get_by_title("Close")).click()

            self.highlight_element(page.get_by_role("button", name="Add New Key-Value"), scroll=False).click()
            self.highlight_element(page.get_by_label("Key"), scroll=False).click()
            self.highlight_element(page.get_by_label("Key"), scroll=False).fill("test_key")
            self.highlight_element(page.get_by_label("Value"), scroll=False).click()
            self.highlight_element(page.get_by_label("Value"), scroll=False).fill("dangerous")
            self.highlight_element(page.get_by_role("button", name="Add", exact=True), scroll=False).click()
            self.highlight_element(page.get_by_role("button", name="Update Links")).click()
            self.highlight_element(page.get_by_role("button", name="Update", exact=True)).click()
            go_to_assess()

        page = taranis_frontend

        go_to_assess()
        enter_hotkey_menu()
        apply_filter()
        assess_workflow_1()
        assess_workflow_2()

    def test_reports(self, taranis_frontend: Page):
        def go_to_analyze():
            self.highlight_element(page.get_by_role("link", name="Analyze").first).click()
            page.wait_for_url("**/analyze", wait_until="domcontentloaded")
            expect(page).to_have_title("Taranis AI | Analyze")

        def go_to_assess():
            self.highlight_element(page.get_by_role("link", name="Assess").first).click()
            page.wait_for_url("**/assess**", wait_until="domcontentloaded")
            expect(page).to_have_title("Taranis AI | Assess")

        def report_1():
            self.highlight_element(page.get_by_role("button", name="New Report").first).click()
            page.wait_for_url("**/report/", wait_until="domcontentloaded")
            self.highlight_element(page.get_by_role("combobox")).click()

            expect(page.get_by_role("listbox")).to_contain_text("CERT Report")
            expect(page.get_by_role("listbox")).to_contain_text("Disinformation")
            expect(page.get_by_role("listbox")).to_contain_text("OSINT Report")
            expect(page.get_by_role("listbox")).to_contain_text("Vulnerability Report")

            time.sleep(0.5)
            page.screenshot(path="./tests/playwright/screenshots/report_item_add.png")

            self.highlight_element(page.get_by_text("CERT Report")).click()
            self.highlight_element(page.get_by_label("Title")).fill("Test Report")
            self.highlight_element(page.get_by_role("button", name="Save")).click()

        def report_2():
            self.highlight_element(page.get_by_role("button", name="New Report")).click()
            self.highlight_element(page.get_by_role("combobox")).click()
            self.highlight_element(page.get_by_text("Disinformation")).click()
            self.highlight_element(page.get_by_label("Title")).fill("Test Disinformation Title")
            self.highlight_element(page.get_by_role("button", name="Save")).click()

        def add_stories_to_report_1():
            page.keyboard.press("Control+A")
            self.highlight_element(page.get_by_role("button", name="add to report")).click()
            self.highlight_element(page.get_by_role("dialog").get_by_label("Open")).click()
            self.highlight_element(page.get_by_role("option", name="Test Report")).click()
            self.highlight_element(page.get_by_role("button", name="add to report").last).click()
            page.keyboard.press("Escape")

            self.highlight_element(
                page.locator("div").filter(has_text="Global Mining Espionage by APT67").nth(5).get_by_role("button").nth(1)
            ).click()
            self.highlight_element(page.get_by_role("dialog").get_by_label("Open")).click()
            self.highlight_element(page.get_by_role("option", name="Test Disinformation Title")).click()
            self.highlight_element(page.get_by_role("button", name="add to report")).click()

        def modify_report_1():
            self.highlight_element(page.get_by_role("cell", name="Test Report")).click()
            self.highlight_element(page.get_by_label("date"), scroll=False).fill("17/3/2024")
            self.highlight_element(page.get_by_label("timeframe"), scroll=False).fill("12/2/2024 - 21/2/2024")
            self.highlight_element(page.get_by_label("handler", exact=True), scroll=False).fill("John Doe")
            self.highlight_element(page.get_by_label("co_handler"), scroll=False).fill("Arthur Doyle")
            self.highlight_element(page.get_by_label("Open").nth(1), scroll=False).click()
            self.highlight_element(page.get_by_text("Global Mining Espionage by APT67", exact=True).nth(1), scroll=False).click()
            self.highlight_element(page.get_by_text("Advanced Phishing Techniques by APT58", exact=True).nth(1), scroll=False).click()
            self.highlight_element(page.get_by_label("Close").last, scroll=False).click()
            self.highlight_element(page.get_by_label("Open").nth(2), scroll=False).click()
            self.highlight_element(page.get_by_text("Genetic Engineering Data Theft by APT81", exact=True).nth(1), scroll=False).click()
            self.highlight_element(page.get_by_label("Close").last, scroll=False).click()
            self.highlight_element(page.get_by_label("Side-by-side"), scroll=False).check()

            self.highlight_element(page.get_by_label("Completed"), scroll=False).check()
            self.highlight_element(page.get_by_role("button", name="Save"), scroll=False).click()
            time.sleep(1)
            page.screenshot(path="./tests/playwright/screenshots/report_item_view.png")

        def check_reports_items_by_tag():
            self.highlight_element(page.get_by_role("button", name="reset filter")).click()
            self.highlight_element(page.get_by_label("Tags", exact=True)).click()
            self.highlight_element(page.get_by_label("Tags", exact=True)).fill("test")
            self.highlight_element(page.get_by_text("Test Report").last).click()
            page.locator(".w-100").click()
            page.keyboard.press("Control+A")
            self.short_sleep(duration=1)
            page.keyboard.press("Control+Space")
            self.short_sleep(duration=1)

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

        go_to_assess()
        check_reports_items_by_tag()

    def test_e2e_publish(self, taranis_frontend: Page):
        page = taranis_frontend

        self.highlight_element(page.get_by_role("link", name="Publish").first).click()
        page.wait_for_url("**/publish", wait_until="domcontentloaded")
        expect(page).to_have_title("Taranis AI | Publish")
        self.highlight_element(page.get_by_role("button", name="New Product").first).click()
        self.highlight_element(page.get_by_role("combobox").locator("div").filter(has_text="Product Type").locator("div")).click()
        self.highlight_element(page.get_by_role("option", name="Default TEXT Presenter")).click()
        self.highlight_element(page.get_by_label("Title")).click()
        self.highlight_element(page.get_by_label("Title")).fill("Test Product")
        self.highlight_element(page.get_by_label("Description")).click()
        self.highlight_element(page.get_by_label("Description")).fill("Test Description")
        self.highlight_element(page.get_by_role("button", name="Save")).click()
        self.highlight_element(page.get_by_role("main").locator("header").get_by_role("button", name="Render Product"))
        page.screenshot(path="./tests/playwright/screenshots/screenshot_publish.png")
