#!/usr/bin/env python3

import pytest
import time
import re
from playwright.sync_api import expect, Page
from playwright_helpers import PlaywrightHelpers


@pytest.mark.e2e_user
@pytest.mark.e2e_ci
@pytest.mark.usefixtures("e2e_ci")
class TestEndToEndUser(PlaywrightHelpers):
    @pytest.mark.e2e_publish
    def test_e2e_login(self, taranis_frontend: Page):
        page = taranis_frontend
        expect(page).to_have_title("Taranis AI", timeout=5000)

        self.add_keystroke_overlay(page)

        expect(page).to_have_title("Taranis AI", timeout=5000)

        self.highlight_element(page.get_by_placeholder("Username"))
        page.get_by_placeholder("Username").fill("admin")
        self.highlight_element(page.get_by_placeholder("Password"))
        page.get_by_placeholder("Password").fill("admin")
        self.highlight_element(page.locator("role=button")).click()
        page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")

    def test_enable_infinite_scroll(self, taranis_frontend: Page):
        page = taranis_frontend
        page.get_by_role("button").nth(1).click()
        page.get_by_text("Settings").click()
        page.get_by_label("Infinite Scroll").check()
        page.get_by_role("button", name="Save").click()
        page.locator("div").filter(has_text="Profile updated").nth(2).click()

    def test_e2e_assess(self, taranis_frontend: Page, e2e_server):
        def go_to_assess():
            self.highlight_element(page.get_by_role("link", name="Assess").first).click()
            page.wait_for_url("**/assess", wait_until="domcontentloaded")
            expect(page).to_have_title("Taranis AI | Assess")

        def assert_stories():
            expect(page.get_by_role("main")).to_contain_text(
                "Genetic Engineering Data Theft by APT81 (8) This story informs about the current security state."
            )
            expect(page.get_by_role("main")).to_contain_text(
                "Article:geneticresearchsecurity.com Author:Irene ThompsonGenetic Engineering Data Theft by APT81APT81 targets national research labs to steal genetic engineering data."
            )
            expect(page.get_by_role("main")).to_contain_text(
                "Article:smartcityupdate.com Author:Bethany WhiteSmart City Sabotage by APT74 in EuropeAPT74 involved in sabotaging smart city projects across Europe."
            )
            expect(page.get_by_role("main")).to_contain_text(
                "Article:mediasecurityfocus.com Author:Charles LeeInternational Media Manipulation by APT75APT75 uses sophisticated cyber attacks to manipulate international media outlets."
            )
            expect(page.get_by_role("main")).to_contain_text(
                "Article:pharmasecuritytoday.com Author:Diana BrooksPharmaceutical Trade Secrets Theft by APT76APT76 implicated in stealing trade secrets from global pharmaceutical companies."
            )
            expect(page.get_by_role("main")).to_contain_text(
                "Article:powergridsecurityfocus.com Author:Evan MoralesPower Grid Disruptions in Asia by APT77APT77 deploys disruptive attacks against national power grids in Asia."
            )
            expect(page.get_by_role("main")).to_contain_text(
                "Article:aerospacesecuritytoday.com Author:Fiona GarciaEspionage in Aerospace Industries by APT78APT78 targets aerospace industries with espionage aimed at stealing futuristic propulsion tech."
            )
            expect(page.get_by_role("main")).to_contain_text(
                "Article:sportseventsecurity.com Author:Gregory PhillipsOlympic Website DDoS Attacks by APT79APT79 conducts large-scale denial of service attacks on major sports events websites during the Olympics."
            )
            expect(page.get_by_role("main")).to_contain_text(
                "Article:telecomsecurityupdate.com Author:Holly JensenGlobal Telecommunications Disrupted by APT80APT80 hacks into satellite communication systems, causing widespread disruptions in global telecommunications."
            )

        def hotkeys():
            self.highlight_element(page.get_by_text("Genetic Engineering Data Theft by APT81")).click()
            self.highlight_element(page.get_by_text("APT73 Exploits Global Shipping Container Systems (5)")).click()
            self.highlight_element(page.get_by_text("Patient Data Harvesting by APT60 (4)")).click()
            self.short_sleep(0.5)
            page.keyboard.press("Control+I")
            self.short_sleep(duration=1)

        def interact_with_story():
            self.highlight_element(page.locator("button:nth-child(5)").first).click()
            time.sleep(0.5)
            page.screenshot(path="./tests/playwright/screenshots/screenshot_story_options.png")

            self.highlight_element(page.locator('[id^="v-menu-"] div > div > a:nth-of-type(1) > div > i').first).click()
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

            # story should contain one attribute "test_key": "dangerous"
            expect(page.locator("table > tbody > tr:nth-of-type(1) > td:nth-of-type(1) > div > div > div > div > input")).to_have_value(
                "test_key"
            )
            expect(page.locator("table > tbody > tr:nth-of-type(1) > td:nth-of-type(2) > div > div > div > div > input")).to_have_value(
                "dangerous"
            )

            self.highlight_element(page.locator(".cm-activeLine").first, scroll=False).click()
            self.highlight_element(
                page.locator("#form div").filter(has_text="Summary91›Enter your summary").get_by_role("textbox"), scroll=False
            ).fill("This story informs about the current security state.")
            self.highlight_element(
                page.locator("#form div").filter(has_text="Comment91›Enter your comment").get_by_role("textbox"), scroll=False
            ).fill("I like this story, it needs to be reviewed.")

            page.screenshot(path="./tests/playwright/screenshots/screenshot_edit_story_1.png")
            self.highlight_element(page.get_by_role("button", name="Update", exact=True), scroll=False).click()
            page.locator("div").filter(has_text="updated").nth(2).click()
            time.sleep(0.5)
            page.screenshot(path="./tests/playwright/screenshots/screenshot_edit_story_2.png")

        def assert_edited_story():
            self.highlight_element(page.locator('[class^="ml-auto mr-auto"] a')).click()

            # title
            expect(page.get_by_label("Title")).to_have_value("Genetic Engineering Data Theft by APT81")

            # summary
            expect(
                page.locator("div").filter(has_text=re.compile(r"^Summary91")).get_by_role("textbox").locator(":first-child")
            ).to_have_text("This story informs about the current security state.")

            # comment
            expect(
                page.locator("div").filter(has_text=re.compile(r"^Comment91")).get_by_role("textbox").locator(":first-child")
            ).to_have_text("I like this story, it needs to be reviewed.")

            # tags
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div:nth-of-type(1) > span > div")).to_have_text("APT75")
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div:nth-of-type(2) > span > div")).to_have_text("APT74")
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div:nth-of-type(3) > span > div")).to_have_text("APT76")
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div:nth-of-type(4) > span > div")).to_have_text("APT77")
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div:nth-of-type(5) > span > div")).to_have_text("APT78")
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div:nth-of-type(6) > span > div")).to_have_text("APT79")
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div:nth-of-type(7) > span > div")).to_have_text("APT80")
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div:nth-of-type(8) > span > div")).to_have_text("APT81")

            # attributes
            expect(page.locator("table > tbody > tr:nth-of-type(1) > td:nth-of-type(1) > div > div > div > div > input")).to_have_value(
                "test_key"
            )
            expect(page.locator("table > tbody > tr:nth-of-type(1) > td:nth-of-type(2) > div > div > div > div > input")).to_have_value(
                "dangerous"
            )
            self.highlight_element(page.get_by_role("button", name="Update", exact=True), scroll=False).click()

        def infinite_scroll_all_items():
            self.smooth_scroll(page.locator("div:nth-child(21)").first)
            self.highlight_element(page.get_by_role("button", name="Load more"), scroll=False).click()
            self.smooth_scroll(page.locator("div:nth-child(31) > .v-container > div"))
            self.highlight_element(page.get_by_role("button", name="Load more"), scroll=False).click()
            self.short_sleep(duration=1)

            self.highlight_element(page.locator('input:near(:text("Items per page"))').first).click()
            self.highlight_element(page.get_by_label("Items per page")).click()
            self.highlight_element(page.get_by_role("option", name="100")).click()

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

        page = taranis_frontend
        self.add_keystroke_overlay(page)

        go_to_assess()
        enter_hotkey_menu()
        infinite_scroll_all_items()

        self.highlight_element(page.get_by_role("button", name="relevance"), scroll=False).click()
        hotkeys()
        page.screenshot(path="./tests/playwright/screenshots/assess_landing_page.png")
        interact_with_story()
        assert_edited_story()

        assert_stories()

        # TODO: uncomment when frontend charts is fixed
        # self.highlight_element(page.get_by_role("button", name="show charts")).click()
        # page.locator("canvas").first.wait_for()

    def test_e2e_analyze(self, e2e_server, taranis_frontend: Page, pic_prefix):
        base_url = e2e_server.url()

        def go_to_analyze():
            self.highlight_element(page.get_by_role("link", name="Analyze").first).click()
            page.wait_for_url("**/analyze", wait_until="domcontentloaded")
            expect(page).to_have_title("Taranis AI | Analyze")

        def report_1():
            self.highlight_element(page.get_by_role("button", name="New Report").first).click()
            page.wait_for_url("**/report/", wait_until="domcontentloaded")
            self.highlight_element(page.get_by_role("combobox")).click()
            time.sleep(0.5)

            expect(page.get_by_role("listbox")).to_contain_text("CERT Report")
            expect(page.get_by_role("listbox")).to_contain_text("Disinformation")
            expect(page.get_by_role("listbox")).to_contain_text("OSINT Report")
            expect(page.get_by_role("listbox")).to_contain_text("Vulnerability Report")

            time.sleep(0.5)
            page.screenshot(path=f"./tests/playwright/screenshots/{pic_prefix}report_item_add.png")

            self.highlight_element(page.get_by_text("CERT Report")).click()
            self.highlight_element(page.get_by_label("Title")).fill("Test Report")
            self.highlight_element(page.get_by_role("button", name="Save")).click()
            page.locator("div").filter(has_text="created").nth(2).click()

        def report_2():
            self.highlight_element(page.get_by_role("button", name="New Report")).click()
            self.highlight_element(page.get_by_role("combobox")).click()
            self.highlight_element(page.get_by_text("Disinformation")).click()
            self.highlight_element(page.get_by_label("Title")).fill("Test Disinformation Title")
            self.highlight_element(page.get_by_role("button", name="Save")).click()
            page.locator("div").filter(has_text="created").nth(2).click()

        def report_3():
            self.highlight_element(page.get_by_role("button", name="New Report")).click()
            page.get_by_role("combobox").click()
            page.get_by_text("OSINT Report").click()
            page.get_by_label("Title").fill("Test OSINT Title")
            page.get_by_role("button", name="Save").click()
            page.locator("div").filter(has_text="created").nth(2).click()

        def report_4():
            page.get_by_role("button", name="New Report").click()
            page.get_by_role("combobox").click()
            page.get_by_text("Vulnerability Report").click()
            page.get_by_label("Title").fill("Test Vulnerability Title")
            page.get_by_role("button", name="Save").click()
            page.locator("div").filter(has_text="created").nth(2).click()

        def add_stories_to_report_1():
            self.highlight_element(page.get_by_role("link", name="Assess")).click()
            self.highlight_element(page.locator("button:below(:text('Global Mining Espionage by APT67 (4)'))").first).click()
            self.highlight_element(page.get_by_role("dialog").get_by_label("Open")).click()
            self.highlight_element(page.get_by_role("option", name="Test Report")).click()
            self.highlight_element(page.get_by_role("button", name="add to report")).click()

            self.highlight_element(page.locator("button:below(:text('Advanced Phishing Techniques by APT58 (3)'))").first).click()
            self.highlight_element(page.get_by_role("dialog").get_by_label("Open")).click()
            self.highlight_element(page.get_by_role("option", name="Test Report")).click()
            self.highlight_element(page.get_by_role("button", name="add to report")).click()

            self.highlight_element(page.locator("button:below(:text('Genetic Engineering Data Theft by APT81 (8)'))").first).click()
            self.highlight_element(page.get_by_role("dialog").get_by_label("Open")).click()
            self.highlight_element(page.get_by_role("option", name="Test Report")).click()
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
            self.highlight_element(page.get_by_role("button", name="Save"), scroll=False).click()
            page.locator("div").filter(has_text="updated").nth(2).click()
            time.sleep(1)
            page.screenshot(path=f"./tests/playwright/screenshots/{pic_prefix}report_item_view.png")

        def assert_analyze():
            expect(page.locator("tbody")).to_contain_text("CERT Report")
            expect(page.locator("tbody")).to_contain_text("Test Report")
            texts = page.locator(
                "table tr:below(:text('stories')) td:nth-of-type(6)"
            ).all_inner_texts()  #  Locate all rows of column `stories`
            assert "3" in texts

        def tag_filter(base_url):
            page.goto(f"{base_url}")  # needed for a refresh; any other reload is failing to load from the live_server
            self.highlight_element(page.get_by_role("link", name="Assess").first).click()
            self.highlight_element(page.get_by_role("button", name="relevance"), scroll=False).click()
            self.highlight_element(page.get_by_label("Tags", exact=True)).click()
            self.highlight_element(page.locator("div").filter(has_text=re.compile(r"^APT75$")).nth(1)).click()
            page.screenshot(path="./tests/playwright/screenshots/screenshot_assess_by_tag.png")

        page = taranis_frontend
        self.add_keystroke_overlay(page)

        go_to_analyze()
        report_1()
        go_to_analyze()
        report_2()
        go_to_analyze()
        report_3()
        go_to_analyze()
        report_4()
        add_stories_to_report_1()

        go_to_analyze()
        modify_report_1()

        go_to_analyze()
        assert_analyze()

        tag_filter(base_url)
        go_to_analyze()

        page.screenshot(path=f"./tests/playwright/screenshots/{pic_prefix}analyze_view.png")

    @pytest.mark.e2e_publish
    def test_e2e_publish(self, taranis_frontend: Page):
        page = taranis_frontend
        self.add_keystroke_overlay(page)

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
        page.get_by_text("Product created").click()
        self.highlight_element(page.get_by_role("main").locator("header").get_by_role("button", name="Render Product"))
        page.screenshot(path="./tests/playwright/screenshots/screenshot_publish.png")
