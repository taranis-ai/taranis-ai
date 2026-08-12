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
        finally:
            page.close()
            context.close()
