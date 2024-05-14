#!/usr/bin/env python3

from playwright.sync_api import expect, Page
import time
import pytest


@pytest.mark.e2e
@pytest.mark.e2e_ci
@pytest.mark.usefixtures("e2e_ci")
class TestEndToEnd:
    wait_duration = 2
    ci_run = False
    produce_artifacts = False

    def scroll_to_the_bottom(self, page, scroll_step=300, max_attempts=10):
        last_height = page.evaluate("document.documentElement.scrollHeight")
        attempts = 0

        while True:
            page.evaluate(f"window.scrollBy(0, {scroll_step})")
            time.sleep(0.5)

            new_height = page.evaluate("document.documentElement.scrollHeight")

            if new_height == last_height:
                attempts += 1
            else:
                attempts = 0

            if attempts >= max_attempts:
                break

            last_height = new_height

    def highlight_element(self, locator):
        if self.ci_run:
            return locator
        style_content = """
        .highlight-element { background-color: yellow; outline: 4px solid red; }
        """

        style_tag = locator.page.add_style_tag(content=style_content)
        locator.evaluate("element => element.classList.add('highlight-element')")
        time.sleep(self.wait_duration)
        locator.evaluate("element => element.classList.remove('highlight-element')")
        locator.page.evaluate("style => style.remove()", style_tag)
        return locator

    def test_e2e_login(self, taranis_frontend: Page):
        page = taranis_frontend
        ###
        # expect(page).to_have_title("Uncomment and halt test run for test writing purposes", timeout=0)
        ###
        # expect(page).to_have_title("Taranis AI", timeout=500)
        self.highlight_element(page.get_by_placeholder("Username"))
        page.get_by_placeholder("Username").fill("admin")
        self.highlight_element(page.get_by_placeholder("Password"))
        page.get_by_placeholder("Password").fill("admin")
        self.highlight_element(page.locator("role=button")).click()
        page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")

    def test_e2e_assess(self, taranis_frontend: Page):
        page = taranis_frontend
        self.highlight_element(page.get_by_role("link", name="Assess").first).click()

        self.scroll_to_the_bottom(page)

        # page.get_by_text("Genetic Engineering Data Theft by APT81APT81 targets national research labs to").click()
        # page.get_by_text("Global Telecommunications Disrupted by APT80APT80 hacks into satellite").click()
        # page.get_by_text("Olympic Website DDoS Attacks by APT79APT79 conducts large-scale denial of").click()
        # page.get_by_text("Espionage in Aerospace Industries by APT78APT78 targets aerospace industries").click()
        # page.get_by_text("Power Grid Disruptions in Asia by APT77APT77 deploys disruptive attacks against").click()
        # page.get_by_text("Pharmaceutical Trade Secrets Theft by APT76APT76 implicated in stealing trade").click()
        # page.get_by_text("International Media Manipulation by APT75APT75 uses sophisticated cyber attacks").click()
        # page.get_by_text("Smart City Sabotage by APT74 in EuropeAPT74 involved in sabotaging smart city").click()
        # page.get_by_role("button", name="merge").click()
        #
        # page.get_by_text("APT73 Exploits Global Shipping Container SystemsAPT73 exploits vulnerabilities").click()
        # page.get_by_text("Major Data Breach at International Museum by APT72APT72 orchestrates major data").click()
        # page.get_by_text("Industrial IoT Disruptions by APT71APT71 exploits industrial IoT devices to").click()
        # page.get_by_text("IoT Botnet Expansion by APT61APT61 exploits vulnerabilities in IoT devices to").click()
        # page.get_by_text("Airport Surveillance Concerns by APT70APT70's new cyber surveillance tools").click()
        # page.get_by_role("button", name="merge").click()

        expect(page).to_have_title("Taranis AI | Assess", timeout=1000)

        self.highlight_element(page.get_by_label("Source", exact=True)).click()

        self.highlight_element(page.get_by_role("option", name="Test Source")).click()
        page.locator("body").press("Escape")

        expect(page.get_by_role("main")).to_contain_text(
            "Bundesinnenministerin Nancy Faeser wird Claudia Plattner zur neuen BSI-Präsidentin berufen"
        )
        expect(page.get_by_role("main")).to_contain_text(
            "Claudia Plattner wird ab 1. Juli 2023 das Bundesamt für Sicherheitin der Informationstechnik (BSI) leiten."
        )
        self.highlight_element(page.locator(".ml-auto > button").first).click()
        expect(page.get_by_role("main")).to_contain_text("TEST CONTENT XXXX")
        expect(page.get_by_role("main")).to_contain_text("Mobile World Congress 2023")
        expect(page.get_by_role("main")).to_contain_text("TEST CONTENT YYYY")
        self.highlight_element(page.locator("div:nth-child(3) > div:nth-child(2) > div > div:nth-child(2) > .ml-auto > button").first).click()
        expect(page.get_by_role("main")).to_contain_text("TEST CONTENT YYYY")
        self.highlight_element(page.get_by_role("heading", name="Bundesinnenministerin Nancy")).click()
        self.highlight_element(page.get_by_text("Mobile World Congress 2023TEST CONTENT YYYY")).click()
        page.screenshot(path="./tests/playwright/screenshots/screenshot_assess_before_merge.png")

        self.highlight_element(page.get_by_role("button", name="merge")).click()
        expect(page.get_by_role("main")).to_contain_text("(2)")
        if self.produce_artifacts:
            page.screenshot(path="tests/playwright/screenshots/assess_final.png")
        self.highlight_element(page.locator(".ml-auto > button").first).click()
        page.screenshot(path="./tests/playwright/screenshots/screenshot_assess.png")

    def test_e2e_analyze(self, taranis_frontend: Page):
        page = taranis_frontend
        self.highlight_element(page.get_by_role("link", name="Analyze").first).click()
        expect(page).to_have_title("Taranis AI | Analyze", timeout=5000)
        self.highlight_element(page.get_by_role("button", name="New Report")).click()
        self.highlight_element(page.get_by_role("combobox")).click()
        # page.click("#report_item_selector")
        expect(page.get_by_role("listbox")).to_contain_text("CERT Report")
        expect(page.get_by_role("listbox")).to_contain_text("Disinformation")
        expect(page.get_by_role("listbox")).to_contain_text("OSINT Report")
        expect(page.get_by_role("listbox")).to_contain_text("Vulnerability Report")
        self.highlight_element(page.get_by_text("CERT Report")).click()
        self.highlight_element(page.get_by_label("Title")).click()
        self.highlight_element(page.get_by_label("Title")).fill("Test Title")
        self.highlight_element(page.get_by_role("button", name="Save")).click()
        self.highlight_element(page.get_by_role("link", name="Assess")).click()
        self.highlight_element(page.get_by_role("main").get_by_role("button").nth(1)).click()
        self.highlight_element(page.get_by_role("dialog").get_by_label("Open")).click()
        self.highlight_element(page.get_by_role("option", name="Test Title")).click()
        self.highlight_element(page.get_by_role("button", name="share")).click()
        self.highlight_element(page.get_by_role("link", name="Analyze")).click()
        expect(page.locator("tbody")).to_contain_text("CERT Report")
        expect(page.locator("tbody")).to_contain_text("Test Title")
        expect(page.locator("tbody")).to_contain_text("1")
        page.screenshot(path="./tests/playwright/screenshots/screenshot_analyze.png")

    def test_e2e_publish(self, taranis_frontend: Page):
        page = taranis_frontend
        self.highlight_element(page.get_by_role("link", name="Publish").first).click()
        expect(page).to_have_title("Taranis AI | Publish", timeout=5000)
        self.highlight_element(page.get_by_role("button", name="New Product")).click()
        self.highlight_element(page.get_by_role("combobox").locator("div").filter(has_text="Product Type").locator("div")).click()
        self.highlight_element(page.get_by_role("option", name="Default TEXT Presenter")).click()
        self.highlight_element(page.get_by_label("Title")).click()
        self.highlight_element(page.get_by_label("Title")).fill("Test Product")
        self.highlight_element(page.get_by_label("Description")).click()
        self.highlight_element(page.get_by_label("Description")).fill("Test Description")
        self.highlight_element(page.get_by_role("button", name="Create")).click()
        self.highlight_element(page.get_by_role("main").locator("header").get_by_role("button", name="Render Product")).click()
        page.screenshot(path="./tests/playwright/screenshots/screenshot_publish.png")
