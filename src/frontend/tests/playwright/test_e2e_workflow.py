import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from base_e2e_test import BaseE2ETest
from flask import url_for
from playwright.sync_api import Page, expect

from tests.external_e2e import allow_requests_passthru


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
        self.highlight_element(page.get_by_test_id("bookmark-mode-new")).click()
        self.highlight_element(page.get_by_test_id("new-bookmark-name")).fill(bookmark_name)
        self.highlight_element(page.get_by_test_id("submit-bookmark-story")).click()
        expect(page.locator("#notification-bar")).to_contain_text("stories bookmarked")

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

    def test_assess(
        self,
        non_admin_logged_in_page: Page,
        forward_console_and_page_errors_non_admin: None,
        stories_date_descending_not_important: list[str],
        stories_date_descending_important: list[str],
    ):
        def mark_story_as_read(story_id: str):
            story_card = page.get_by_test_id(f"story-card-{story_id}")
            self.highlight_element(story_card.get_by_test_id("story-summary"))
            expect(story_card.get_by_test_id("story-summary")).to_be_visible()
            self.highlight_element(story_card.get_by_test_id("story-actions-menu")).click()
            self.highlight_element(story_card.get_by_test_id("toggle-read")).click()

        def toggle_story_summary(story_id: str):
            story_card = page.get_by_test_id(f"story-card-{story_id}")
            self.highlight_element(story_card.get_by_test_id("toggle-summary")).click()

        def open_story_detail(story_id: str):
            story_card = page.get_by_test_id(f"story-card-{story_id}")
            self.highlight_element(story_card.get_by_test_id("toggle-summary")).click()
            self.highlight_element(story_card.get_by_test_id("open-detail-view")).click()
            expect(page.get_by_test_id("story-title")).to_be_visible()

        def set_story_filters(read: str | None = None, important: str | None = None):
            if read is not None:
                self.highlight_element(page.get_by_label("Read")).select_option(read)
            if important is not None:
                self.highlight_element(page.get_by_label("Important")).select_option(important)

        def reset_story_filters():
            self.highlight_element(page.get_by_role("link", name="Reset filters ctrl+esc")).click()

        def assert_story_count(expected_count: str):
            expect(page.get_by_test_id("assess_story_count").get_by_text(expected_count)).to_be_visible()

        def go_to_assess():
            self.navigate_to_assess(page)

        def apply_filter():
            self.highlight_element(page.get_by_role("radio", name="Shift")).check()
            set_story_filters(read="true")
            set_story_filters(read="false")
            set_story_filters(important="false")
            set_story_filters(important="true")
            reset_story_filters()
            set_story_filters(important="true")
            assert_story_count("5")
            reset_story_filters()
            set_story_filters(read="false", important="false")

        def assess_workflow_1(non_important_story_ids: list[str]):
            # Check summary and mark as read
            assert len(non_important_story_ids) == 28

            # first story
            story_card = page.get_by_test_id(f"story-card-{non_important_story_ids[0]}")
            self.highlight_element(story_card.get_by_test_id("story-summary"), scroll=False)
            expect(story_card.get_by_test_id("story-summary")).to_be_visible()
            mark_story_as_read(non_important_story_ids[0])

            # next story
            story_card = page.get_by_test_id(f"story-card-{non_important_story_ids[1]}")
            self.highlight_element(story_card.get_by_test_id("story-summary"), scroll=False)
            expect(story_card.get_by_test_id("story-summary")).to_be_visible()
            mark_story_as_read(non_important_story_ids[1])

            for i in range(2, 7):
                mark_story_as_read(non_important_story_ids[i])

            # select multiple, press mark as read once
            for i in range(7, 10):
                self.highlight_element(
                    page.get_by_test_id(f"story-card-{non_important_story_ids[i]}").get_by_test_id("story-actions-menu")
                ).click()
                self.highlight_element(page.get_by_test_id(f"story-card-{non_important_story_ids[i]}"), scroll=False).click()
            self.highlight_element(page.get_by_role("button", name="Mark as read")).click()
            expect(page.get_by_test_id("assess_story_selection_count")).to_be_hidden()
            expect(page.get_by_test_id(f"story-card-{non_important_story_ids[10]}")).to_be_visible()

            # remaining stories
            for i in range(10, 20):
                mark_story_as_read(non_important_story_ids[i])

            # after all stories are marked as read in first page, last story is carried over -> mark it twice
            mark_story_as_read(non_important_story_ids[19])

            for i in range(20, 28):
                print(f"Marking story {non_important_story_ids[i]} as read AND is {i}/28")
                mark_story_as_read(non_important_story_ids[i])

        def assess_workflow_2(important_story_ids: list[str]):
            set_story_filters(important="true")

            # Show/unshow details of all stories
            for story_id in important_story_ids[:5]:
                toggle_story_summary(story_id)
                toggle_story_summary(story_id)

            # Open specific story
            open_story_detail(important_story_ids[0])

            # Mark as read and remove important (using manual clicks since base method may not fit)
            self.highlight_element(page.get_by_test_id("story-actions-menu")).click()
            self.highlight_element(page.get_by_test_id("toggle-read")).click()
            # Remove mark as important
            self.highlight_element(page.get_by_test_id("story-actions-menu")).click()
            self.highlight_element(page.get_by_test_id("toggle-important")).click()

            go_to_assess()
            reset_story_filters()
            set_story_filters(read="false", important="true")

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

            page.get_by_test_id("edit-newsitem-tags").first.click()
            page.get_by_test_id("news-item-tag-name-input").last.fill("Austria")
            page.get_by_test_id("news-item-tag-value-input").last.fill("Location")
            page.get_by_role("button", name="Save tags").click()
            page.get_by_role("button", name="Add attribute").click()
            page.get_by_test_id("attribute-key-input").last.fill("Analyst_1")
            page.get_by_test_id("attribute-value-input").last.fill("read")
            page.get_by_role("button", name="Save changes").click()

            go_to_assess()

        #           Run test
        # ============================

        page = non_admin_logged_in_page

        go_to_assess()
        # test_hotkey_menu()
        apply_filter()
        assess_workflow_1(stories_date_descending_not_important)
        assess_workflow_2(stories_date_descending_important)

    def test_reports(
        self,
        non_admin_logged_in_page: Page,
        forward_console_and_page_errors_non_admin: None,
        stories_date_descending: list[str],
    ):
        def go_to_analyze():
            self.navigate_to_analyze(page)

        def report_1():
            self.highlight_element(page.get_by_role("button", name="New Report").first).click()
            page.get_by_label("Select a report").select_option("CERT Report")
            self.short_sleep(0.5)
            page.get_by_label("Title", exact=True).fill("Test Report")
            self.highlight_element(page.get_by_role("button", name="Create Report")).click()
            time.sleep(0.5)
            self.capture_screenshot(page, "./tests/playwright/screenshots/report_item_add.png")

        def report_2():
            self.highlight_element(page.get_by_role("button", name="New Report")).click()
            page.get_by_label("Select a report").select_option("Disinformation")
            page.get_by_label("Title", exact=True).fill("Test Disinformation Title")
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

        def modify_report_1(stories_date_descending: list[str]):
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
        add_stories_to_report_1()

        go_to_analyze()

        modify_report_1(stories_date_descending)

        # TODO: tag search not implemented yet
        # go_to_assess()
        # check_reports_items_by_tag()

    def test_e2e_publish(self, non_admin_logged_in_page: Page, forward_console_and_page_errors_non_admin: None):
        page = non_admin_logged_in_page

        self.highlight_element(page.get_by_role("link", name="Publish").first).click()
        page.wait_for_url("**/publish", wait_until="domcontentloaded")
        # expect(page).to_have_title("Taranis AI | Publish")

        self.highlight_element(page.get_by_role("button", name="New Product").first).click()
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
