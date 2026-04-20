from flask import url_for
from playwright.sync_api import Page, expect
from playwright_helpers import PlaywrightHelpers


class BaseE2ETest(PlaywrightHelpers):
    """Base class for E2E tests with common CRUD operations and shared logic."""

    def login_with_credentials(
        self,
        page: Page,
        username: str = "admin",
        password: str = "admin",
    ):
        """Perform login with given credentials."""
        page.goto(url_for("base.login", _external=True))
        expect(page).to_have_title("Taranis AI", timeout=5000)

        self.add_keystroke_overlay(page)

        self.highlight_element(page.get_by_placeholder("Username"))
        page.get_by_placeholder("Username").fill(username)
        self.highlight_element(page.get_by_placeholder("Password"))
        page.get_by_placeholder("Password").fill(password)
        login_button = page.get_by_test_id("login-button")
        expect(login_button).to_be_visible(timeout=10000)
        self.highlight_element(login_button).click()
        page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")
        expect(page.locator("#dashboard")).to_be_visible()

    def navigate_to_list(self, page: Page, url_endpoint: str, table_test_id: str):
        """Navigate to admin list page and verify table visibility."""
        page.goto(url_for(url_endpoint, _external=True))
        expect(page.get_by_test_id(table_test_id)).to_be_visible()
        page.screenshot(path=f"./tests/playwright/screenshots/docs_{url_endpoint.split('.')[-1]}.png")

    def fill_form_field(self, page: Page, label: str, value: str, exact: bool = True, required: bool = False):
        """Fill a form field by label, with optional required validation."""
        field = page.get_by_label(label, exact=exact)
        if required:
            expect(field).to_have_attribute("required", "")
        field.fill(value)

    def select_form_option(self, page: Page, label: str, value: str):
        """Select an option from a dropdown by label."""
        page.get_by_label(label).select_option(value)

    def submit_form(self, page: Page, submit_locator: str):
        """Submit a form and highlight the submit button."""
        submit_button = page.locator(submit_locator)
        self.highlight_element(submit_button).click()

    def delete_table_row(
        self,
        page: Page,
        delete_button_test_id: str,
        confirm: bool = True,
        confirm_button_name: str = "OK",
    ):
        """Delete row by explicit delete action test id."""
        assert delete_button_test_id, "delete_table_row requires delete_button_test_id"
        delete_button = page.get_by_test_id(delete_button_test_id)
        assert delete_button.count() == 1, f"Expected exactly one delete button '{delete_button_test_id}', found {delete_button.count()}"
        expect(delete_button).to_be_visible(timeout=10000)
        delete_button.click()
        if confirm:
            page.get_by_role("button", name=confirm_button_name).click()

    def assert_item_in_table(self, page: Page, table_test_id: str, item_name: str):
        """Assert that an item appears in a table."""
        expect(page.get_by_test_id(table_test_id).get_by_role("link", name=item_name)).to_be_visible()

    def assert_item_not_in_table(self, page: Page, table_test_id: str, item_name: str):
        """Assert that an item does not appear in a table."""
        expect(page.get_by_test_id(table_test_id).get_by_role("link", name=item_name)).not_to_be_visible()

    def create_item(
        self,
        page: Page,
        new_button_test_id: str,
        text_fields: dict[str, str],
        submit_locator: str,
        select_fields: dict[str, str] | None = None,
    ):
        """Create a new item by filling form fields."""
        page.get_by_test_id(new_button_test_id).click()
        for label, value in text_fields.items():
            self.fill_form_field(page, label, value, exact=False)
        for label, value in (select_fields or {}).items():
            self.select_form_option(page, label, value)
        self.submit_form(page, submit_locator)

    def update_item(
        self,
        page: Page,
        item_name: str,
        text_fields: dict[str, str],
        submit_locator: str,
        select_fields: dict[str, str] | None = None,
    ):
        """Update an existing item."""
        page.get_by_role("link", name=item_name).click()
        for label, value in text_fields.items():
            self.fill_form_field(page, label, value, exact=False)
        for label, value in (select_fields or {}).items():
            self.select_form_option(page, label, value)
        self.submit_form(page, submit_locator)

    def delete_item(self, page: Page, table_test_id: str, item_name: str, delete_button_test_id: str):
        """Delete an item."""
        self.delete_table_row(page, delete_button_test_id)
        self.assert_item_not_in_table(page, table_test_id, item_name)

    # Navigation methods for workflow tests
    def navigate_to_assess(self, page: Page):
        """Navigate to Assess page."""
        self.highlight_element(page.get_by_role("link", name="Assess").first).click()
        page.wait_for_url("**/assess**", wait_until="domcontentloaded")

    def navigate_to_analyze(self, page: Page):
        """Navigate to Analyze page."""
        self.highlight_element(page.get_by_role("link", name="Analyze").first).click()
        page.wait_for_url("**/analyze", wait_until="domcontentloaded")

    def navigate_to_publish(self, page: Page):
        """Navigate to Publish page."""
        self.highlight_element(page.get_by_role("link", name="Publish").first).click()
        page.wait_for_url("**/publish", wait_until="domcontentloaded")

    # Story interaction methods
    def mark_story_as_read(self, page: Page, story_id: str):
        """Mark a story as read."""
        story_card = page.get_by_test_id(f"story-card-{story_id}")
        self.highlight_element(story_card.get_by_test_id("story-summary"))
        expect(story_card.get_by_test_id("story-summary")).to_be_visible()
        self.highlight_element(story_card.get_by_test_id("story-actions-menu")).click()
        self.highlight_element(story_card.get_by_test_id("toggle-read")).click()

    def toggle_story_summary(self, page: Page, story_id: str):
        """Toggle story summary visibility."""
        story_card = page.get_by_test_id(f"story-card-{story_id}")
        self.highlight_element(story_card.get_by_test_id("toggle-summary")).click()

    def open_story_detail(self, page: Page, story_id: str):
        """Open story detail view."""
        story_card = page.get_by_test_id(f"story-card-{story_id}")
        self.highlight_element(story_card.get_by_test_id("toggle-summary")).click()
        self.highlight_element(story_card.get_by_test_id("open-detail-view")).click()
        expect(page.get_by_test_id("story-title")).to_be_visible(timeout=10000)

    def set_story_filters(self, page: Page, read: str | None = None, important: str | None = None):
        """Set story filters."""
        if read is not None:
            self.highlight_element(page.get_by_label("Read")).select_option(read)
        if important is not None:
            self.highlight_element(page.get_by_label("Important")).select_option(important)

    def reset_story_filters(self, page: Page):
        """Reset story filters."""
        self.highlight_element(page.get_by_role("link", name="Reset filters ctrl+esc")).click()

    # Assertion methods
    def assert_dashboard_sections_visible(self, page: Page, sections: list[str]):
        """Assert dashboard sections are visible."""
        for section in sections:
            expect(page.locator("#dashboard")).to_contain_text(section)

    def assert_story_count(self, page: Page, expected_count: str):
        """Assert story count matches expected."""
        expect(page.get_by_test_id("assess_story_count").get_by_text(expected_count)).to_be_visible()
