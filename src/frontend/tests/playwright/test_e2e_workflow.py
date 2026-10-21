import re
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse
from uuid import uuid4

import pytest
from base_e2e_test import BaseE2ETest
from flask import url_for
from playwright.sync_api import Page, expect

from tests.external_e2e import allow_requests_passthru, external_core_api_url, external_frontend_base_url


@pytest.fixture
def demo_chat_provider(core_request_client):
    if external_core_api_url() or external_frontend_base_url():
        pytest.skip("The scripted chat demo requires the isolated local E2E stack")

    allow_requests_passthru()
    settings = core_request_client.json_request("GET", "/settings/settings")["items"][0]["settings"]
    endpoint = core_request_client.json_request(
        "POST",
        "/settings/llm-endpoints",
        json_data={"name": "Landing page demo", "base_url": "http://demo-llm:8080/v1", "enabled": True, "api_format": "responses"},
    )
    news_item_ids = []
    story_ids = []
    try:
        core_request_client.patch("/settings/settings", json_data={"settings": {"llm_chat_endpoint": endpoint["id"]}})
        for index, title in enumerate(
            [
                "Ransomware campaign targets European hospitals",
                "New ransomware advisory urges rapid patching",
                "Manufacturing sector strengthens ransomware defenses",
            ]
        ):
            timestamp = datetime.now(UTC).isoformat()
            created = core_request_client.json_request(
                "POST",
                "/assess/news-items",
                json_data={
                    "id": str(uuid4()),
                    "title": title,
                    "content": "Demo intelligence for the landing-page chat walkthrough.",
                    "link": f"https://example.invalid/chat-demo/{index}",
                    "source": "manual",
                    "osint_source_id": "manual",
                    "published": timestamp,
                    "collected": timestamp,
                },
            )
            news_item_ids.extend(created["news_item_ids"])
            story_ids.append(created["story_id"])
            core_request_client.patch(f"/assess/stories/{created['story_id']}", json_data={"read": index == 2})
        yield story_ids
    finally:
        try:
            core_request_client.patch(
                "/settings/settings", json_data={"settings": {"llm_chat_endpoint": settings.get("llm_chat_endpoint", "")}}
            )
        finally:
            try:
                core_request_client.post(f"/settings/llm-endpoints/{endpoint['id']}/delete", json_data={})
            finally:
                for news_item_id in news_item_ids:
                    core_request_client.delete(f"/assess/news-items/{news_item_id}", raise_for_status=False)


@pytest.mark.usefixtures("e2e_ci")
@pytest.mark.e2e_user_workflow
@pytest.mark.usefixtures("ensure_basic_user_permissions")
class TestUserWorkflow(BaseE2ETest):
    ALL_ATTRIBUTE_REPORT_TYPE_LABEL = "Zzz_All Attribute Types Report"

    def test_e2e_login(self, taranis_frontend: Page):
        page = taranis_frontend
        self.login_with_credentials(page, username="user", password="test")
        self.assert_dashboard_sections_visible(page, ["Assess", "Analyze", "Publish", "Connectors"])
        assert page.get_by_role("link", name="Administration").count() == 0

    def test_instance_setup(
        self,
        non_admin_logged_in_page: Page,
        forward_console_and_page_errors_non_admin: None,
        fake_source: str,
    ):
        page = non_admin_logged_in_page
        self.navigate_to_assess(page)
        expect(page.get_by_test_id("assess")).to_be_visible()
        assert page.get_by_role("link", name="Administration").count() == 0
        expect(page.get_by_role("searchbox", name="Select sources")).to_be_visible()

    @pytest.mark.e2e_ci
    def test_analyst_review_guides_triage_into_report_and_publish(
        self,
        non_admin_logged_in_page: Page,
        forward_console_and_page_errors_non_admin: None,
        pre_seed_report_type_all_attribute_types_optional: None,
        core_request_client,
    ):
        page = non_admin_logged_in_page
        report_title = f"Analyst Review {uuid4().hex[:8]}"
        original_statuses: dict[str, tuple[bool, bool]] = {}
        created_news_item_ids: list[str] = []
        created_story_ids: list[str] = []
        report_id: str | None = None

        try:
            allow_requests_passthru()
            snapshot = core_request_client.json_request("GET", "/assess/analyst-review/snapshot")
            for story_id in snapshot["story_ids"]:
                story = core_request_client.json_request("GET", f"/assess/stories/{story_id}")
                original_statuses[story_id] = (bool(story["read"]), bool(story["important"]))
                core_request_client.patch(f"/assess/stories/{story_id}", json_data={"read": True})

            now = datetime.now(UTC)
            for index in range(3):
                news_item_id = str(uuid4())
                timestamp = (now - timedelta(seconds=index)).isoformat()
                response = core_request_client.json_request(
                    "POST",
                    "/assess/news-items",
                    json_data={
                        "id": news_item_id,
                        "title": f"Analyst review story {index + 1}",
                        "content": f"Analyst review summary {index + 1}",
                        "link": f"https://example.invalid/analyst-review/{news_item_id}",
                        "source": "manual",
                        "osint_source_id": "manual",
                        "published": timestamp,
                        "collected": timestamp,
                    },
                )
                created_news_item_ids.extend(response["news_item_ids"])
                created_story_ids.append(response["story_id"])
                core_request_client.patch(
                    f"/assess/stories/{response['story_id']}",
                    json_data={"important": True},
                )

            page.goto(url_for("base.dashboard", _external=True))
            expect(page.get_by_test_id("start-analyst-review-card")).to_be_visible()
            page.get_by_test_id("start-analyst-review-card").get_by_role("link", name="Start analyst review").click()
            expect(page.get_by_test_id("analyst-review-start")).to_be_visible()

            page.get_by_test_id("analyst-review-report-title").fill(report_title)
            page.get_by_test_id("analyst-review-report-type").select_option(label=self.ALL_ATTRIBUTE_REPORT_TYPE_LABEL)
            expect(page.get_by_test_id("analyst-review-new-review-report")).to_be_checked()
            page.get_by_test_id("create-and-start-analyst-review").click()

            story_card = page.get_by_test_id("analyst-review-story")
            expect(story_card).to_be_visible()
            first_story_id = story_card.get_attribute("data-story-id")
            assert first_story_id in created_story_ids
            page.keyboard.press("a")
            expect(page.get_by_test_id("analyst-review-progress")).to_contain_text("1 of 3 reviewed")

            second_story_id = story_card.get_attribute("data-story-id")
            assert second_story_id in created_story_ids and second_story_id != first_story_id
            page.keyboard.press("d")
            expect(page.get_by_test_id("analyst-review-progress")).to_contain_text("2 of 3 reviewed")

            third_story_id = story_card.get_attribute("data-story-id")
            assert third_story_id in created_story_ids and third_story_id not in {first_story_id, second_story_id}
            page.keyboard.press("s")
            page.wait_for_url("**/report/*?review_run=*", wait_until="domcontentloaded")

            expect(page.get_by_test_id("analyst-review-report-step")).to_be_visible()
            expect(page.get_by_test_id(f"story-link-{first_story_id}")).to_be_visible()
            expect(page.locator("[data-testid^='story-link-']")).to_have_count(1)
            report_id = page.get_by_test_id("report-id").inner_text().removeprefix("ID: ").strip()
            page.get_by_test_id("save-report").click()
            page.wait_for_url("**/publish/0?report_id=*", wait_until="domcontentloaded")

            expect(page.get_by_role("heading", name="Create Product")).to_be_visible()
            expect(page.locator(f'input[type="hidden"][name="report_items[]"][value="{report_id}"]')).to_have_count(1)

            first_story = core_request_client.json_request("GET", f"/assess/stories/{first_story_id}")
            second_story = core_request_client.json_request("GET", f"/assess/stories/{second_story_id}")
            third_story = core_request_client.json_request("GET", f"/assess/stories/{third_story_id}")
            assert (first_story["read"], first_story["important"]) == (True, False)
            assert (second_story["read"], second_story["important"]) == (True, False)
            assert (third_story["read"], third_story["important"]) == (False, True)

            report = core_request_client.json_request("GET", f"/analyze/report-items/{report_id}")
            assert [story["id"] for story in report["stories"]] == [first_story_id]
        finally:
            if report_id:
                core_request_client.delete(f"/analyze/report-items/{report_id}", raise_for_status=False)
            for news_item_id in created_news_item_ids:
                core_request_client.delete(f"/assess/news-items/{news_item_id}", raise_for_status=False)
            for story_id, (read, important) in original_statuses.items():
                core_request_client.patch(
                    f"/assess/stories/{story_id}",
                    json_data={"read": read, "important": important},
                    raise_for_status=False,
                )

    def test_assess_filter_token_select_reopens_after_selection(
        self,
        non_admin_logged_in_page: Page,
        forward_console_and_page_errors_non_admin,
        stories_session_wrapper,
    ):
        page = non_admin_logged_in_page
        self.navigate_to_assess(page)

        def assert_filter_reopens(filter_id: str, searchbox_name: str, option_label: str, selected_label: str):
            section = page.locator(f'[data-filter-id="{filter_id}"]')
            searchbox = page.get_by_role("searchbox", name=searchbox_name)
            suggestion_list = section.get_by_role("listbox")

            self.highlight_element(searchbox).click()
            expect(suggestion_list).to_be_visible()
            expect(section.get_by_role("button", name=option_label)).to_be_visible()
            self.highlight_element(section.get_by_role("button", name=option_label)).click()
            self.wait_for_htmx_settled(page)

            expect(page.locator(f'[data-test-id="{filter_id}-selected"]')).to_contain_text(selected_label)
            expect(suggestion_list).not_to_be_visible()

            reopened_section = page.locator(f'[data-filter-id="{filter_id}"]')
            reopened_searchbox = page.get_by_role("searchbox", name=searchbox_name)
            reopened_suggestion_list = reopened_section.get_by_role("listbox")
            self.highlight_element(reopened_searchbox).click()
            expect(reopened_suggestion_list).to_be_visible()
            reopened_searchbox.press("Escape")
            expect(reopened_suggestion_list).not_to_be_visible()

        assert_filter_reopens("source-filter", "Select sources", "Test Source", "Test Source")
        assert_filter_reopens("language-filter", "Select languages", "EN", "EN")

        tag_section = page.locator('[data-filter-id="tag-filter"]')
        tag_searchbox = page.get_by_role("searchbox", name="Search tags")
        tag_suggestion_list = tag_section.get_by_role("listbox")
        self.highlight_element(tag_searchbox).click()
        expect(tag_suggestion_list).not_to_be_visible()
        tag_searchbox.fill("tag")
        expect(tag_suggestion_list).to_be_visible()

    @pytest.mark.e2e_ci
    def test_story_bookmarks(
        self,
        non_admin_logged_in_page: Page,
        forward_console_and_page_errors_non_admin: None,
        stories_date_descending: list[str],
    ):
        page = non_admin_logged_in_page
        bookmark_name = f"E2E Bookmark {uuid4()}"
        selected_story_ids = stories_date_descending[:2]

        self.navigate_to_assess(page)
        for story_id in selected_story_ids:
            self.highlight_element(page.get_by_test_id(f"story-card-{story_id}"), scroll=False).click()

        self.highlight_element(page.get_by_role("button", name="Bookmark")).click()
        expect(page.get_by_test_id("story-bookmark-dialog")).to_be_visible()
        self.highlight_element(page.get_by_test_id("new-bookmark-name")).fill(bookmark_name)
        self.highlight_element(page.get_by_test_id("submit-bookmark-story")).click()
        expect(page.locator("#notification-bar")).to_contain_text("Bookmark collections updated")

        for story_id in selected_story_ids:
            card = page.get_by_test_id(f"story-card-{story_id}")
            expect(card.get_by_test_id("bookmark-story")).to_have_text("Saved")
            expect(card).to_have_attribute("aria-selected", "true")

        first_card = page.get_by_test_id(f"story-card-{selected_story_ids[0]}")
        first_card.get_by_test_id("bookmark-story").click()
        picker = page.get_by_test_id("story-bookmark-dialog")
        first_choice = picker.locator("label").filter(has_text=bookmark_name).locator('input[name="bookmark_ids"]')
        expect(first_choice).to_be_checked()
        picker.get_by_role("radio", name=f"Use {bookmark_name} for quick-save", exact=True).check()
        extra_name = f"Extra {uuid4()}"
        picker.get_by_test_id("new-bookmark-name").fill(extra_name)
        picker.get_by_test_id("submit-bookmark-story").click()
        expect(picker).not_to_be_visible()

        # Bulk saves preserve mixed memberships, including rows hidden by search.
        page.get_by_role("button", name="Bookmark", exact=True).click()
        picker = page.get_by_test_id("story-bookmark-dialog")
        partial = picker.locator("label").filter(has_text=extra_name).locator('input[name="bookmark_ids"]')
        expect(partial).to_have_js_property("indeterminate", True)
        picker.get_by_role("searchbox", name="Find a collection").fill(bookmark_name)
        expect(partial).not_to_be_visible()
        picker.get_by_test_id("submit-bookmark-story").click()
        expect(picker).not_to_be_visible()

        # A failed inline create retains the current membership and entered name.
        first_card.get_by_test_id("bookmark-story").click()
        picker.get_by_test_id("new-bookmark-name").fill(bookmark_name)
        picker.get_by_test_id("submit-bookmark-story").click()
        expect(page.locator("#notification-bar")).to_contain_text("already exists")
        expect(picker).to_be_visible()
        expect(picker.get_by_test_id("new-bookmark-name")).to_have_value(bookmark_name)
        expect(picker.locator("label").filter(has_text=extra_name).locator('input[name="bookmark_ids"]')).to_be_checked()
        picker.get_by_role("button", name="Cancel", exact=True).click()

        # Quick-save and undo update cards without dropping the current selection.
        third_card = page.get_by_test_id(f"story-card-{stories_date_descending[2]}")
        third_card.get_by_test_id("bookmark-story").click()
        expect(page.locator("#notification-bar")).to_contain_text(f"Saved to {bookmark_name}")
        expect(third_card.get_by_test_id("bookmark-story")).to_have_text("Saved")
        page.locator('[data-test-id="bookmark-undo"]').click()
        expect(third_card.get_by_test_id("bookmark-story")).to_have_text("Bookmark")
        expect(first_card).to_have_attribute("aria-selected", "true")
        page.reload(wait_until="domcontentloaded")
        expect(first_card.get_by_test_id("bookmark-story")).to_have_text("Saved")

        self.highlight_element(page.get_by_role("link", name="Bookmarks")).click()
        page.wait_for_url("**/bookmarks", wait_until="domcontentloaded")
        expect(page.get_by_test_id("bookmarks-page")).to_be_visible()
        target_card = page.locator("[data-testid^='bookmark-card-']").filter(has_text=bookmark_name)
        expect(target_card).to_be_visible()

        self.highlight_element(page.locator("[data-testid^='open-bookmark-']").filter(has_text=bookmark_name)).click()
        page.wait_for_url("**/bookmarks/*", wait_until="domcontentloaded")
        expect(page.get_by_test_id("bookmark-detail")).to_be_visible()
        for story_id in selected_story_ids:
            expect(page.get_by_test_id(f"story-card-{story_id}")).to_be_visible()

        selected_card = page.get_by_test_id(f"story-card-{selected_story_ids[0]}")
        self.highlight_element(selected_card, scroll=False).click()
        expect(selected_card).to_have_attribute("aria-selected", "true")
        assert "bg-primary/5" in (selected_card.get_attribute("class") or "")
        self.highlight_element(page.get_by_test_id("bookmark-remove-selected")).click()
        confirm_button = page.locator(".swal2-container .swal2-confirm")
        expect(confirm_button).to_be_visible()
        confirm_button.click()
        self.wait_for_htmx_settled(page)
        expect(page.get_by_test_id(f"story-card-{selected_story_ids[0]}")).not_to_be_visible()
        expect(page.get_by_test_id(f"story-card-{selected_story_ids[1]}")).to_be_visible()

        self.highlight_element(page.get_by_test_id("delete-bookmark-detail")).click()
        confirm_button = page.locator(".swal2-container .swal2-confirm")
        expect(confirm_button).to_be_visible()
        confirm_button.click()
        page.wait_for_url("**/bookmarks", wait_until="domcontentloaded")
        expect(page.get_by_text(bookmark_name)).not_to_be_visible()
        self.wait_for_htmx_settled(page)

    @pytest.mark.e2e_ci
    def test_chat(
        self,
        demo_chat_provider: list[str],
        non_admin_logged_in_page: Page,
        forward_console_and_page_errors_non_admin: None,
        core_request_client,
        access_token_basic,
    ):
        page = non_admin_logged_in_page
        conversation_id = None
        try:
            self.highlight_element(page.get_by_test_id("nav-chat")).click()
            page.wait_for_url("**/chat", wait_until="domcontentloaded")
            expect(page.get_by_test_id("chat-help")).to_be_visible()
            expect(page.get_by_test_id("chat-configuration-warning")).not_to_be_visible()

            self.highlight_element(page.get_by_test_id("chat-input")).fill("Find ransomware stories in my collection.")
            self.highlight_element(page.get_by_test_id("chat-send")).click()
            page.wait_for_url("**/chat/*", wait_until="domcontentloaded")
            conversation_id = page.url.rsplit("/", 1)[-1]
            answer = page.get_by_test_id("chat-message-assistant")
            expect(answer).to_have_count(1)
            expect(answer).to_contain_text("Ransomware campaign targets European hospitals")
            expect(answer.locator("time")).to_be_visible()
            expect(answer.locator("time")).to_have_attribute("datetime", re.compile(r".+Z$"))
            self.highlight_element(answer.locator(".chat-bubble"))

            self.highlight_element(page.get_by_test_id("chat-input")).fill("Which of those stories are still unread?")
            self.highlight_element(page.get_by_test_id("chat-send")).click()
            expect(answer).to_have_count(2)
            expect(answer.last).to_contain_text("unread ransomware")
            expect(answer.last).not_to_contain_text("Manufacturing sector")
            timestamps = page.locator("#chat-messages time")
            expect(timestamps).to_have_count(4)
            saved_timestamps = timestamps.all_text_contents()
            assert all(timestamp.strip() for timestamp in saved_timestamps)
            self.highlight_element(answer.last.locator(".chat-bubble"))
            self.capture_screenshot(page, "./tests/playwright/screenshots/screenshot_chat.png")

            self.highlight_element(page.get_by_test_id("chat-new")).click()
            expect(page.get_by_test_id("chat-help")).to_be_visible()
            self.highlight_element(page.get_by_test_id("chat-history-item").filter(has_text="Find ransomware stories")).click()
            expect(answer).to_have_count(2)
            expect(page.get_by_test_id("chat-message-user")).to_have_count(2)
            expect(timestamps).to_have_text(saved_timestamps)

            self.highlight_element(page.get_by_test_id("chat-assess-link").last).click()
            expect(page.get_by_test_id("assess")).to_be_visible()
            expect(page.get_by_role("combobox", name="Read", exact=True)).to_have_value("false")
            for story_id in demo_chat_provider[:2]:
                expect(page.get_by_test_id(f"story-card-{story_id}")).to_be_visible()
            expect(page.get_by_test_id(f"story-card-{demo_chat_provider[2]}")).not_to_be_visible()

            evidence_story = page.get_by_test_id(f"story-card-{demo_chat_provider[0]}")
            self.highlight_element(evidence_story.get_by_test_id("open-detail-view")).click()
            page.wait_for_url(
                lambda url: urlparse(url).path == url_for("assess.story", story_id=demo_chat_provider[0]),
                wait_until="domcontentloaded",
            )
            expect(page.get_by_test_id("news-item-title")).to_have_text("Ransomware campaign targets European hospitals")
            evidence = page.get_by_role("paragraph").filter(has_text="Demo intelligence for the landing-page chat walkthrough.")
            expect(evidence).to_be_visible()
            evidence.scroll_into_view_if_needed()
            self.highlight_element(evidence)
        finally:
            if conversation_id:
                core_request_client.with_access_token(access_token_basic).delete(f"/chat/conversations/{conversation_id}")

    def test_assess(
        self,
        non_admin_logged_in_page: Page,
        forward_console_and_page_errors_non_admin: None,
        stories_session_wrapper,
    ):
        page = non_admin_logged_in_page
        self.navigate_to_assess(page)
        read_filter = page.get_by_role("combobox", name="Read", exact=True)
        important_filter = page.get_by_role("combobox", name="Important", exact=True)
        read_filter.select_option("")
        important_filter.select_option("")
        self.wait_for_htmx_settled(page)

        story_cards = page.locator("[data-testid^='story-card-'][data-story-read='false'][data-story-important='false']")
        expect(story_cards.nth(1)).to_be_visible()
        story_ids = story_cards.evaluate_all("cards => cards.slice(0, 2).map(card => card.dataset.storyId)")
        for story_id in story_ids:
            card = page.get_by_test_id(f"story-card-{story_id}")
            self.highlight_element(card.get_by_test_id("story-summary"))
            self.highlight_element(card.get_by_test_id("story-actions-menu")).click()
            self.highlight_element(card.get_by_test_id("toggle-read")).click()
            expect(card).to_have_attribute("data-story-read", "true")

        for story_id in story_ids:
            card = page.get_by_test_id(f"story-card-{story_id}")
            self.highlight_element(card.get_by_test_id("story-actions-menu")).click()
            self.highlight_element(card.get_by_test_id("toggle-important")).click()
            expect(card).to_have_attribute("data-story-important", "true")

        for story_id in story_ids:
            card = page.get_by_test_id(f"story-card-{story_id}")
            expect(card).to_be_visible()
            expect(card).to_have_attribute("data-story-read", "true")
            expect(card).to_have_attribute("data-story-important", "true")
        self.highlight_element(page.get_by_test_id(f"story-card-{story_ids[0]}").get_by_test_id("story-title"))
        self.capture_screenshot(page, "./tests/playwright/screenshots/screenshot_assess_triage.png")

    def test_reports(
        self,
        non_admin_logged_in_page: Page,
        forward_console_and_page_errors_non_admin: None,
        stories_session_wrapper,
    ):
        def go_to_analyze():
            self.navigate_to_analyze(page)

        def report_1():
            self.highlight_element(page.get_by_test_id("new-report-button")).click()
            self.highlight_element(page.get_by_role("textbox", name="Title", exact=True)).fill("Test Report")
            self.highlight_element(page.get_by_test_id("report-type-select")).select_option(label="CERT Report")
            self.highlight_element(page.get_by_test_id("save-report")).click()
            expect(page.get_by_role("button", name="Completed", exact=True)).to_be_visible()
            self.capture_screenshot(page, "./tests/playwright/screenshots/report_item_add.png")

        def report_2():
            self.highlight_element(page.get_by_test_id("new-report-button")).click()
            self.highlight_element(page.get_by_role("textbox", name="Title", exact=True)).fill("Test Disinformation Title")
            self.highlight_element(page.get_by_test_id("report-type-select")).select_option(label="Disinformation")
            self.highlight_element(page.get_by_test_id("save-report")).click()
            expect(page.get_by_role("button", name="Completed", exact=True)).to_be_visible()

        def add_stories_to_report_1():
            page.goto(url_for("assess.assess", _external=True, limit=50))
            expect(page.get_by_test_id("assess")).to_be_visible()
            story_cards = page.locator("[data-testid^='story-card-']")
            expect(story_cards.first).to_be_visible()
            selected_story_ids = story_cards.evaluate_all("cards => cards.map(card => card.dataset.storyId)")
            # Select all
            self.highlight_element(page.get_by_test_id("assess-select-all-button")).click()
            self.highlight_element(page.get_by_role("button", name="Add to Report")).click()

            # First dialog
            self.highlight_element(page.get_by_test_id("select-report-input")).select_option(label="Test Report")
            self.highlight_element(page.get_by_test_id("share-to-report-dialog-button")).click()
            expect(page.get_by_test_id("share-story-to-report-dialog")).to_have_count(0)

            # Second dialog
            page.goto(url_for("assess.assess", _external=True, limit=50))
            story_card = page.get_by_test_id(f"story-card-{selected_story_ids[0]}")
            self.highlight_element(story_card).click(position={"x": 5, "y": 5})
            expect(story_card).to_have_attribute("aria-selected", "true")
            self.highlight_element(page.get_by_role("button", name="Add to Report")).click()

            self.highlight_element(page.get_by_test_id("select-report-input")).select_option(label="Test Disinformation Title")
            self.highlight_element(page.get_by_test_id("share-to-report-dialog-button")).click()
            expect(page.get_by_test_id("share-story-to-report-dialog")).to_have_count(0)
            return selected_story_ids

        def modify_report_1(selected_story_ids: list[str]):
            self.highlight_element(page.get_by_role("link", name="Test Report", exact=True)).click()
            self.expect_list_of_test_ids_visible(page, [f"story-link-{story_id}" for story_id in selected_story_ids])
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
            self.expect_list_of_test_ids_visible(page, [f"story-link-{story_id}" for story_id in selected_story_ids])

            self.highlight_element(page.get_by_role("button", name="Stacked view")).click()
            self.expect_list_of_test_ids_visible(page, [f"story-link-{story_id}" for story_id in selected_story_ids])

            self.highlight_element(page.get_by_role("button", name="Split view")).click()
            self.expect_list_of_test_ids_visible(page, [f"story-link-{story_id}" for story_id in selected_story_ids])

            self.highlight_element(page.get_by_role("button", name="Completed")).click()
            self.expect_list_of_test_ids_visible(page, [f"story-link-{story_id}" for story_id in selected_story_ids])

            # TODO: see if needed:
            # page.get_by_test_id("save-report").click()
            time.sleep(1)
            self.capture_screenshot(page, "./tests/playwright/screenshots/report_item_view.png")

        #           Run test
        # ============================

        page = non_admin_logged_in_page

        go_to_analyze()
        report_1()
        go_to_analyze()
        report_2()
        go_to_analyze()
        expect(page.get_by_text("Test Report")).to_be_visible()
        expect(page.get_by_text("Test Disinformation Title")).to_be_visible()

        self.highlight_element(page.get_by_role("link", name="Assess")).click()
        selected_story_ids = add_stories_to_report_1()

        go_to_analyze()

        modify_report_1(selected_story_ids)

        # TODO: tag search not implemented yet
        # go_to_assess()
        # check_reports_items_by_tag()

    def test_e2e_publish(self, non_admin_logged_in_page: Page, forward_console_and_page_errors_non_admin: None):
        page = non_admin_logged_in_page

        self.highlight_element(page.get_by_role("link", name="Publish").first).click()
        page.wait_for_url("**/publish", wait_until="domcontentloaded")
        # expect(page).to_have_title("Taranis AI | Publish")

        self.highlight_element(page.get_by_role("link", name="New Product").first).click()
        self.highlight_element(page.get_by_label("Product Type * Select an item")).click()
        page.get_by_label("Product Type * Select an item").select_option(label="CERT Daily Report")

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
        self.capture_screenshot(page, "./tests/playwright/screenshots/screenshot_publish.png")
