import re
from uuid import uuid4

import pytest
from flask import url_for
from playwright.sync_api import Browser, Page, expect

from tests.external_e2e import external_basic_auth_credentials


@pytest.mark.e2e_user
@pytest.mark.e2e_ci
@pytest.mark.usefixtures("e2e_ci", "ensure_basic_user_permissions")
class TestNoJavaScriptLayout:
    def test_assess_keeps_sidebar_and_stories_visible_without_javascript(
        self,
        browser: Browser,
        browser_context_args,
        e2e_request_context,
        pre_seed_stories,
    ):
        context = browser.new_context(**browser_context_args, java_script_enabled=False)
        page: Page = context.new_page()
        username, password = external_basic_auth_credentials()

        try:
            page.goto(url_for("base.login", _external=True))
            page.get_by_placeholder("Username").fill(username)
            page.get_by_placeholder("Password").fill(password)
            page.get_by_test_id("login-button").click()
            expect(page.locator("#dashboard")).to_be_visible()

            page.goto(url_for("assess.assess", _external=True))
            expect(page.get_by_test_id("assess")).to_be_visible()
            expect(page.get_by_role("heading", name=pre_seed_stories[0]["title"])).to_be_visible()

            search_input = page.get_by_placeholder("Search stories")
            search_input.fill(pre_seed_stories[0]["title"])
            search_input.press("Enter")
            page.wait_for_url(re.compile(r"[?&]search="), wait_until="domcontentloaded")
            expect(page.get_by_role("heading", name=pre_seed_stories[0]["title"])).to_be_visible()
            expect(page.get_by_role("searchbox", name="Select sources")).to_be_hidden()
            expect(page.get_by_role("searchbox", name="Search tags")).to_be_hidden()
            expect(page.get_by_test_id("language-filter-native")).to_be_visible()

            page.locator('#assess-sidebar select[name="sort"]').select_option("date_asc")
            page.get_by_test_id("assess-apply-filters").click()
            page.wait_for_url(re.compile(r"[?&]sort=date_asc(?:&|$)"), wait_until="domcontentloaded")
            assert "search=" in page.url
            expect(page.get_by_role("heading", name=pre_seed_stories[0]["title"])).to_be_visible()

            story_id = pre_seed_stories[0]["story_id"]
            sidebar = page.locator("#sidebar")
            main = page.get_by_role("main")
            sidebar_box = sidebar.bounding_box()
            main_box = main.bounding_box()

            assert sidebar_box is not None
            assert main_box is not None
            assert sidebar_box["width"] == pytest.approx(256)
            assert main_box["x"] == pytest.approx(sidebar_box["width"])
            expect(page.locator("#assess-top-bar")).to_be_hidden()

            story_card = page.get_by_test_id(f"story-card-{story_id}")
            story_card.get_by_test_id("story-actions-menu").click()
            story_card.get_by_test_id("share-story").click()
            page.wait_for_url("**/story/sharing**", wait_until="domcontentloaded")
            expect(page.get_by_role("heading", name="Share Story")).to_be_visible()
            page.get_by_role("link", name="Add to report").click()
            page.wait_for_url("**/story/report**", wait_until="domcontentloaded")
            expect(page.get_by_role("heading", name="Add to Report")).to_be_visible()
            expect(page.get_by_role("link", name="New Report")).to_be_visible()

            page.goto(url_for("assess.share_story", story_id=story_id, _external=True))
            expect(page.get_by_role("link", name="Share via email")).to_be_visible()

            page.goto(url_for("assess.assess", _external=True))
            story_card = page.get_by_test_id(f"story-card-{story_id}")
            story_card.get_by_test_id("story-actions-menu").click()
            expect(story_card.get_by_test_id("toggle-read")).to_be_visible()
            story_card.get_by_test_id("toggle-read").click()
            page.wait_for_url("**/story/**", wait_until="domcontentloaded")
            expect(page.get_by_test_id(f"story-card-{story_id}")).to_have_attribute("data-story-read", "true")

            page.goto(url_for("assess.assess", _external=True))
            story_card = page.get_by_test_id(f"story-card-{story_id}")
            story_card.get_by_test_id("story-actions-menu").click()
            story_card.get_by_test_id("bookmark-story").click()
            page.wait_for_url("**/story/**", wait_until="domcontentloaded")

            page.goto(url_for("assess.bookmarks", _external=True))
            page.locator('[data-testid^="open-bookmark-"]').first.click()
            page.wait_for_url("**/bookmarks/**", wait_until="domcontentloaded")
            expect(page.get_by_test_id("bookmark-detail")).to_be_visible()
            expect(page.locator("#assess-top-bar")).to_be_hidden()
        finally:
            page.close()
            context.close()

    def test_report_and_product_crud_without_javascript(
        self,
        browser: Browser,
        browser_context_args,
        e2e_request_context,
    ):
        context = browser.new_context(**browser_context_args, java_script_enabled=False)
        page: Page = context.new_page()
        username, password = external_basic_auth_credentials()

        try:
            page.goto(url_for("base.login", _external=True))
            page.get_by_placeholder("Username").fill(username)
            page.get_by_placeholder("Password").fill(password)
            page.get_by_test_id("login-button").click()
            expect(page.locator("#dashboard")).to_be_visible()

            report_title = f"No JavaScript report {uuid4()}"
            page.goto(url_for("analyze.analyze", _external=True))
            page.get_by_test_id("new-report-button").click()
            page.wait_for_url("**/report/0", wait_until="domcontentloaded")
            page.get_by_test_id("report-type-select").select_option(
                page.get_by_test_id("report-type-select").locator("option:not([disabled])").first.get_attribute("value")
            )
            page.locator("#report-title").fill(report_title)
            page.get_by_test_id("save-report").click()
            page.wait_for_url(re.compile(r"/report/(?!0(?:[/?]|$))[^/?]+"), wait_until="domcontentloaded")
            assert page.get_by_test_id("report-id").inner_text() != "ID: 0"

            product_title = f"No JavaScript product {uuid4()}"
            page.goto(url_for("publish.publish", _external=True))
            page.get_by_test_id("new-product-button").click()
            page.wait_for_url("**/publish/0", wait_until="domcontentloaded")
            product_type = page.locator('select[name="product_type_id"]')
            product_type.select_option(product_type.locator("option:not([disabled])").first.get_attribute("value"))
            page.get_by_placeholder("Title").fill(product_title)
            page.get_by_test_id("save-product").click()
            page.wait_for_url(re.compile(r"/publish/(?!0(?:[/?]|$))[^/?]+"), wait_until="domcontentloaded")
            expect(page.get_by_role("heading", name=re.compile(r"Update Product"))).to_be_visible()
            expect(page.get_by_test_id("report-items-native")).to_be_visible()
            report_checkbox = page.get_by_label(report_title, exact=True)
            expect(report_checkbox).to_be_visible()
            report_checkbox.check()
            page.get_by_test_id("save-product").click()
            page.wait_for_load_state("domcontentloaded")
            expect(page.get_by_label(report_title, exact=True)).to_be_checked()

            page.goto(url_for("publish.publish", _external=True))
            product_row = page.get_by_test_id("product-table").locator("tr", has=page.get_by_role("link", name=product_title, exact=True))
            product_row.locator('[data-testid^="action-delete-"]').click()
            page.wait_for_url("**/publish", wait_until="domcontentloaded")
            expect(page.get_by_role("link", name=product_title, exact=True)).to_have_count(0)

            page.goto(url_for("analyze.analyze", _external=True))
            report_row = page.get_by_test_id("report-table").locator("tr", has=page.get_by_role("link", name=report_title, exact=True))
            report_row.locator('[data-testid^="action-delete-"]').click()
            page.wait_for_url("**/analyze", wait_until="domcontentloaded")
            expect(page.get_by_role("link", name=report_title, exact=True)).to_have_count(0)
        finally:
            page.close()
            context.close()
