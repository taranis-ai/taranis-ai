#!/usr/bin/env python3

import pytest
import time
from playwright.sync_api import expect, Page, Locator
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
        self.highlight_element(page.get_by_role("button", name="login")).click()
        page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")

    def test_user_settings(self, taranis_frontend: Page):
        page = taranis_frontend
        page.get_by_test_id("user-menu-button").click()
        page.get_by_text("Settings").click()
        page.get_by_label("Infinite Scroll").check()
        page.get_by_text("Advanced Story Options").check()
        page.get_by_role("button", name="Save").click()
        page.locator("div").filter(has_text="Profile updated").nth(2).click()

    def test_e2e_assess(
        self, taranis_frontend: Page, stories: list, story_news_items: dict, stories_date_descending: list, stories_relevance_descending: list
    ):
        def go_to_assess():
            self.highlight_element(page.get_by_role("link", name="Assess").first).click()
            page.wait_for_url("**/assess", wait_until="domcontentloaded")
            expect(page).to_have_title("Taranis AI | Assess")

        def assert_first_story_and_news_items(story_ids: list, story_news_items: dict):
            # story
            expect(page.get_by_test_id(f"story-card-{story_ids[0]}").get_by_role("heading")).to_contain_text(
                "Genetic Engineering Data Theft by APT81"
            )
            expect(page.get_by_test_id(f"story-card-{story_ids[0]}").get_by_test_id("summarized-content-span")).to_contain_text(
                "This story informs about the current security state."
            )

            # attached news items
            news_item_ids = [news_item.id for news_item in story_news_items[story_ids[0]]]

            # 1
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[0]}").get_by_role("heading")).to_contain_text(
                "Genetic Engineering Data Theft by APT81"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[0]}").get_by_test_id("summarized-content-span")).to_contain_text(
                "APT81 targets national research labs to steal genetic engineering data."
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[0]}").get_by_role("row", name="Article:")).to_contain_text(
                "geneticresearchsecurity.com"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[0]}").get_by_role("row", name="Author:")).to_contain_text(
                "Irene Thompson"
            )

            # 2
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[1]}").get_by_role("heading")).to_contain_text(
                "Smart City Sabotage by APT74 in Europe"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[1]}").get_by_test_id("summarized-content-span")).to_contain_text(
                "APT74 involved in sabotaging smart city projects across Europe."
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[1]}").get_by_role("row", name="Article:")).to_contain_text(
                "smartcityupdate.com"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[1]}").get_by_role("row", name="Author:")).to_contain_text(
                "Bethany White"
            )

            # 3
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[2]}").get_by_role("heading")).to_contain_text(
                "International Media Manipulation by APT75"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[2]}").get_by_test_id("summarized-content-span")).to_contain_text(
                "APT75 uses sophisticated cyber attacks to manipulate international media outlets."
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[2]}").get_by_role("row", name="Article:")).to_contain_text(
                "mediasecurityfocus.com"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[2]}").get_by_role("row", name="Author:")).to_contain_text(
                "Charles Lee"
            )

            # 4
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[3]}").get_by_role("heading")).to_contain_text(
                "Pharmaceutical Trade Secrets Theft by APT76"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[3]}").get_by_test_id("summarized-content-span")).to_contain_text(
                "APT76 implicated in stealing trade secrets from global pharmaceutical companies."
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[3]}").get_by_role("row", name="Article:")).to_contain_text(
                "pharmasecuritytoday.com"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[3]}").get_by_role("row", name="Author:")).to_contain_text(
                "Diana Brooks"
            )

            # 5
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[4]}").get_by_role("heading")).to_contain_text(
                "Power Grid Disruptions in Asia by APT7"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[4]}").get_by_test_id("summarized-content-span")).to_contain_text(
                "APT77 deploys disruptive attacks against national power grids in Asia."
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[4]}").get_by_role("row", name="Article:")).to_contain_text(
                "powergridsecurityfocus.com"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[4]}").get_by_role("row", name="Author:")).to_contain_text(
                "Evan Morales"
            )

            # 6
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[5]}").get_by_role("heading")).to_contain_text(
                "Espionage in Aerospace Industries by APT78"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[5]}").get_by_test_id("summarized-content-span")).to_contain_text(
                "APT78 targets aerospace industries with espionage aimed at stealing futuristic propulsion tech."
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[5]}").get_by_role("row", name="Article:")).to_contain_text(
                "aerospacesecuritytoday.com"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[5]}").get_by_role("row", name="Author:")).to_contain_text(
                "Fiona Garcia"
            )

            # 7
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[6]}").get_by_role("heading")).to_contain_text(
                "Olympic Website DDoS Attacks by APT79"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[6]}").get_by_test_id("summarized-content-span")).to_contain_text(
                "APT79 conducts large-scale denial of service attacks on major sports events websites during the Olympics."
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[6]}").get_by_role("row", name="Article:")).to_contain_text(
                "sportseventsecurity.com"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[6]}").get_by_role("row", name="Author:")).to_contain_text(
                "Gregory Phillips"
            )

            # 8
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[7]}").get_by_role("heading")).to_contain_text(
                "Global Telecommunications Disrupted by APT80"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[7]}").get_by_test_id("summarized-content-span")).to_contain_text(
                "APT80 hacks into satellite communication systems, causing widespread disruptions in global telecommunications."
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[7]}").get_by_role("row", name="Article:")).to_contain_text(
                "telecomsecurityupdate.com"
            )
            expect(page.get_by_test_id(f"news-item-card-{news_item_ids[7]}").get_by_role("row", name="Author:")).to_contain_text(
                "Holly Jensen"
            )

        def filter_by_cybersecurity(story_ids: list, story_news_items_dict: dict):
            # classify all news items in second story as cybersecurity - yes
            page.evaluate("window.scrollTo(0, 0)")
            page.get_by_test_id(f"story-card-{story_ids[1]}").click()
            time.sleep(0.5)
            page.keyboard.press("Control+E")
            self.highlight_element(
                page.get_by_test_id(f"news-item-{story_news_items_dict[story_ids[1]][0].id}-cybersec-yes-btn"), scroll=True
            ).click()
            self.highlight_element(
                page.get_by_test_id(f"news-item-{story_news_items_dict[story_ids[1]][1].id}-cybersec-yes-btn"), scroll=True
            ).click()
            self.highlight_element(
                page.get_by_test_id(f"news-item-{story_news_items_dict[story_ids[1]][2].id}-cybersec-yes-btn"), scroll=True
            ).click()
            self.highlight_element(
                page.get_by_test_id(f"news-item-{story_news_items_dict[story_ids[1]][3].id}-cybersec-yes-btn"), scroll=True
            ).click()
            self.highlight_element(
                page.get_by_test_id(f"news-item-{story_news_items_dict[story_ids[1]][4].id}-cybersec-yes-btn"), scroll=True
            ).click()
            # assert correct status
            self.highlight_element(page.get_by_test_id("story-cybersec-status-chip"), scroll=True)
            expect(page.get_by_test_id("story-cybersec-status-chip")).to_have_text("Yes")
            self.highlight_element(page.get_by_role("link", name="Assess").first).click()

            # classify all news items in third story as cybersecurity - no
            page.evaluate("window.scrollTo(0, 0)")
            page.get_by_test_id(f"story-card-{story_ids[2]}").click()
            time.sleep(0.5)
            page.keyboard.press("Control+E")
            self.highlight_element(
                page.get_by_test_id(f"news-item-{story_news_items_dict[story_ids[2]][0].id}-cybersec-no-btn"), scroll=True
            ).click()
            self.highlight_element(
                page.get_by_test_id(f"news-item-{story_news_items_dict[story_ids[2]][1].id}-cybersec-no-btn"), scroll=True
            ).click()
            self.highlight_element(
                page.get_by_test_id(f"news-item-{story_news_items_dict[story_ids[2]][2].id}-cybersec-no-btn"), scroll=True
            ).click()
            self.highlight_element(
                page.get_by_test_id(f"news-item-{story_news_items_dict[story_ids[2]][3].id}-cybersec-no-btn"), scroll=True
            ).click()
            # assert correct status
            self.highlight_element(page.get_by_test_id("story-cybersec-status-chip"), scroll=True)
            expect(page.get_by_test_id("story-cybersec-status-chip")).to_have_text("No")
            self.highlight_element(page.get_by_role("link", name="Assess").first).click()

            # filter yes - no - mixed - incomplete
            page.evaluate("window.scrollTo(0, 0)")
            self.highlight_element(page.get_by_test_id("filter-cybersecurity-btn")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{story_ids[1]}"))
            self.highlight_element(page.get_by_test_id("filter-cybersecurity-btn")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{story_ids[2]}"))
            self.highlight_element(page.get_by_test_id("filter-cybersecurity-btn")).click()
            self.highlight_element(page.get_by_test_id("filter-cybersecurity-btn")).click()
            self.highlight_element(page.get_by_test_id(f"story-card-{story_ids[0]}"))
            self.highlight_element(page.get_by_test_id("filter-cybersecurity-btn")).click()

        def hotkeys():
            self.highlight_element(page.get_by_text("Genetic Engineering Data Theft by APT81")).click()
            self.highlight_element(page.get_by_text("APT73 Exploits Global Shipping Container Systems (5)")).click()
            self.highlight_element(page.get_by_text("Patient Data Harvesting by APT60 (4)")).click()
            self.short_sleep(0.5)
            page.keyboard.press("Control+I")
            self.short_sleep(duration=1)

        def check_attributes_table(table_locator: Locator, expected_rows: list[list[str]]):
            rows = table_locator.locator("table tbody tr")
            count = rows.count()

            actual_rows = [
                [(rows.nth(i).locator("td").nth(j).locator("input").get_attribute("value") or "").strip() for j in range(2)]
                for i in range(count)
            ]

            assert sorted(actual_rows) == sorted(expected_rows)

        def interact_with_story(story_ids):
            self.highlight_element(page.get_by_test_id(f"story-actions-div-{story_ids[0]}").get_by_test_id("show story-actions-menu")).click()
            time.sleep(0.5)
            page.screenshot(path="./tests/playwright/screenshots/screenshot_story_options.png")

            self.highlight_element(page.get_by_test_id(f"story-actions-menu-{story_ids[0]}").get_by_title("edit story")).click()
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

            check_attributes_table(page.get_by_test_id("attributes-table"), [["test_key", "dangerous"]])

            self.highlight_element(page.locator("div[name='summary']").get_by_role("textbox"), scroll=False).fill(
                "This story informs about the current security state."
            )
            self.highlight_element(page.locator("div[name='comment']").get_by_role("textbox"), scroll=False).fill(
                "I like this story, it needs to be reviewed."
            )
            page.screenshot(path="./tests/playwright/screenshots/screenshot_edit_story_1.png")
            self.highlight_element(page.get_by_role("button", name="Update", exact=True), scroll=False).click()
            page.locator("div").filter(has_text="updated").nth(2).click()
            time.sleep(0.5)
            page.screenshot(path="./tests/playwright/screenshots/screenshot_edit_story_2.png")

        def assert_edited_story(story_ids, story_news_items_dict):
            page.get_by_test_id("story-go-back-btn").click()
            self.highlight_element(page.get_by_test_id(f"story-actions-div-{story_ids[0]}").get_by_test_id("edit story")).click()

            expect(page.get_by_label("Title")).to_have_value("Genetic Engineering Data Theft by APT81")
            expect(page.locator("div[name='summary']").get_by_role("textbox")).to_have_text(
                "This story informs about the current security state."
            )

            expect(page.locator("div[name='comment']").get_by_role("textbox")).to_have_text("I like this story, it needs to be reviewed.")

            # Tag chips
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div.v-chip__content").nth(0)).to_have_text("APT75")
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div.v-chip__content").nth(1)).to_have_text("APT74")
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div.v-chip__content").nth(2)).to_have_text("APT76")
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div.v-chip__content").nth(3)).to_have_text("APT77")
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div.v-chip__content").nth(4)).to_have_text("APT78")
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div.v-chip__content").nth(5)).to_have_text("APT79")
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div.v-chip__content").nth(6)).to_have_text("APT80")
            expect(page.get_by_label("Tags", exact=True).locator("xpath=..").locator("div.v-chip__content").nth(7)).to_have_text("APT81")

            page.get_by_test_id("show-all-attributes").click()
            check_attributes_table(page.get_by_test_id("attributes-table"), [["TLP", "clear"], ["test_key", "dangerous"]])

            # manually classify first three news items
            self.highlight_element(
                page.get_by_test_id(f"news-item-{story_news_items_dict[story_ids[0]][0].id}-cybersec-yes-btn"), scroll=True
            ).click()
            self.highlight_element(
                page.get_by_test_id(f"news-item-{story_news_items_dict[story_ids[0]][1].id}-cybersec-no-btn"), scroll=True
            ).click()
            self.highlight_element(
                page.get_by_test_id(f"news-item-{story_news_items_dict[story_ids[0]][2].id}-cybersec-yes-btn"), scroll=True
            ).click()
            self.highlight_element(page.get_by_role("button", name="Update", exact=True), scroll=True).click()
            page.get_by_test_id("story-go-back-btn").click()

        def infinite_scroll_all_items(stories_date_descending):
            self.smooth_scroll(page.get_by_test_id(f"story-card-{stories_date_descending[19]}"))
            self.highlight_element(page.get_by_role("button", name="Load more"), scroll=False).click()
            self.smooth_scroll(page.get_by_test_id(f"story-card-{stories_date_descending[37]}"))
            self.highlight_element(page.get_by_role("button", name="Load more"), scroll=False).click()
            self.short_sleep(duration=1)
            self.highlight_element(page.get_by_test_id("filter-navigation-div").get_by_role("textbox", name="search")).click()
            self.highlight_element(page.get_by_test_id("filter-navigation-div").get_by_role("textbox", name="Items per page")).click()
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
        infinite_scroll_all_items(stories_date_descending)

        self.highlight_element(page.get_by_role("button", name="relevance"), scroll=False).click()
        hotkeys()
        page.screenshot(path="./tests/playwright/screenshots/assess_landing_page.png")
        interact_with_story(stories)
        assert_edited_story(stories, story_news_items)

        assert_first_story_and_news_items(stories, story_news_items)
        self.highlight_element(page.get_by_role("link", name="Assess").first).click()
        filter_by_cybersecurity(stories_relevance_descending, story_news_items)

        # TODO: uncomment when frontend charts is fixed
        # self.highlight_element(page.get_by_role("button", name="show charts")).click()
        # page.locator("canvas").first.wait_for()

    def test_e2e_analyze(self, e2e_server, taranis_frontend: Page, pic_prefix: str, stories_relevance_descending: list):
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

        def add_stories_to_report_1(stories_relevance_descending: list):
            self.highlight_element(page.get_by_role("link", name="Assess")).click()

            self.highlight_element(
                page.get_by_test_id(f"story-card-{stories_relevance_descending[2]}").get_by_test_id("add to report")
            ).click()
            self.highlight_element(page.get_by_role("dialog").get_by_label("Open")).click()
            self.highlight_element(page.get_by_role("option", name="Test Report")).click()
            self.highlight_element(page.get_by_role("button", name="add to report")).click()

            self.highlight_element(
                page.get_by_test_id(f"story-card-{stories_relevance_descending[4]}").get_by_test_id("add to report")
            ).click()
            self.highlight_element(page.get_by_role("dialog").get_by_label("Open")).click()
            self.highlight_element(page.get_by_role("option", name="Test Report")).click()
            self.highlight_element(page.get_by_role("button", name="add to report")).click()

            self.highlight_element(
                page.get_by_test_id(f"story-card-{stories_relevance_descending[0]}").get_by_test_id("add to report")
            ).click()
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

            # add/remove story chips to vulnerabilities field
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
            self.highlight_element(page.locator("#v-menu-v-42").get_by_text("APT75")).click()
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
        add_stories_to_report_1(stories_relevance_descending)

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
