#!/usr/bin/env python3
import uuid
import pytest
from flask import url_for

from playwright.sync_api import Page, expect
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

    def test_user_dashboard(self, logged_in_page: Page, forward_console_and_page_errors):
        page = logged_in_page

        page.goto(url_for("base.dashboard", _external=True))
        expect(page.locator("#dashboard")).to_be_visible()

    def test_user_assess(self, logged_in_page: Page, forward_console_and_page_errors, pre_seed_stories):
        page = logged_in_page

        def go_to_assess():
            page.goto(url_for("assess.assess", _external=True))
            expect(page.get_by_test_id("assess")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/user_assess.png")

        def access_story():
            story_articles = page.locator("#story-list article")
            story = story_articles.nth(0)
            title = story.locator("h2[data-testid='story-title']").inner_text()
            # published_date = story.locator("span.text-xs").first.inner_text()
            # summary = story.locator("div.prose").inner_text()
            # link = story.locator("a[data-testid^='story-link']").get_attribute("href")
            story.get_by_test_id("toggle-summary").click()

            story.get_by_test_id("toggle-summary").click()
            story.get_by_test_id("toggle-read").click()
            story.get_by_test_id("toggle-important").click()
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

        go_to_assess()
        access_story()
        infinite_scroll_all_items()

    def test_user_analyze(self, logged_in_page: Page, forward_console_and_page_errors, pre_seed_report_stories):
        # self.ci_run = True
        page = logged_in_page
        report_story_one, report_story_two = pre_seed_report_stories
        story_search_term = " ".join(report_story_one["title"].split()[:2])
        story_search_term_lower = story_search_term.lower()
        report_story_two_primary_link = report_story_two["news_items"][0]["link"]

        def go_to_analyze():
            page.goto(url_for("analyze.analyze", _external=True))
            expect(page.get_by_test_id("analyze")).to_be_visible()
            page.screenshot(path="./tests/playwright/screenshots/user_analyze.png")

        def create_report():
            page.get_by_test_id("new-report-button").click()
            page.get_by_role("textbox", name="Title").fill("Test report")
            page.get_by_label("Report Type Select a report").select_option("4")
            expect(page.locator("#report_form")).to_contain_text("Attributes will be generated after the report item has been created.")
            expect(page.get_by_test_id("analyze").locator("section")).to_contain_text("No stories assigned to this report.")
            page.get_by_test_id("save-report").click()
            page.get_by_placeholder("Date").fill("1.1.2000")
            page.get_by_placeholder("Timeframe").fill("January")
            page.get_by_placeholder("Handler", exact=True).fill("Kluger")
            page.get_by_placeholder("CO-Handler").fill("Mensch")
            page.get_by_test_id("save-report").click()

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

            page.get_by_role("link", name="Analyze").click()

            page.get_by_role("link", name="Analyze").click()
            page.get_by_role("link", name="Test report").click()
            page.get_by_test_id(f"remove-story-{report_story_one['id']}").click()

            page.get_by_role("link", name="Assess").click()
            page.get_by_placeholder("Search stories").fill(story_search_term_lower)
            page.get_by_placeholder("Search stories").press("Enter")
            expect(page.get_by_test_id("assess").get_by_text("In Reports")).to_be_visible()  # only one should be in a report now

            page.get_by_role("link", name="Analyze").click()
            page.get_by_test_id("report-table").get_by_role("button").first.click()
            page.get_by_role("row", name="Test report").get_by_role("link").nth(4).click()
            page.get_by_test_id("report-new-product").click()
            expect(page.get_by_role("heading", name="Create Product")).to_be_visible()
            expect(page.get_by_text("Create Product").first).to_be_visible()
            page.get_by_role("link", name="Analyze").click()
            page.get_by_test_id("report-table").get_by_role("button").nth(3).click()
            page.get_by_role("button", name="OK").click()
            page.get_by_role("link", name="Test report").click()
            expect(page.get_by_test_id("report-stories").locator("label")).to_contain_text(report_story_two["title"])
            expect(page.get_by_test_id(f"story-link-{report_story_two['id']}")).to_contain_text(report_story_two_primary_link)

        go_to_analyze()
        create_report()
        add_stories_to_report()

    def test_publish(self, logged_in_page: Page, forward_console_and_page_errors, pre_seed_stories):
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
