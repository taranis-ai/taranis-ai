import re

from flask import url_for
from playwright.sync_api import Page, expect
from playwright_helpers import PlaywrightHelpers


class BaseE2ETest(PlaywrightHelpers):
    """Base class for shared E2E workflow and table interaction helpers."""

    def _get_table_link_locator(self, page: Page, table_id: str, link_text: str):
        """Return the first table cell anchor matched via shared table macro test ids."""
        table = page.get_by_test_id(table_id)
        exact_link_text = re.compile(rf"^\s*{re.escape(link_text)}\s*$")
        return table.locator(f"a[data-testid^='{table_id}_']").filter(has_text=exact_link_text).first

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
        expect(login_button).to_be_visible()
        self.highlight_element(login_button).click()
        page.screenshot(path="./tests/playwright/screenshots/screenshot_login.png")
        expect(page.locator("#dashboard")).to_be_visible()

    def delete_table_row(self, page: Page, delete_button_test_id: str, confirm: bool = True, force: bool = False):
        """Delete row by explicit delete action test id."""
        assert delete_button_test_id, "delete_table_row requires delete_button_test_id"
        delete_button = page.get_by_test_id(delete_button_test_id)
        assert delete_button.count() == 1, f"Expected exactly one delete button '{delete_button_test_id}', found {delete_button.count()}"
        expect(delete_button).to_be_visible()
        delete_button.click()
        row_locator = delete_button.locator("xpath=ancestor::tr[1]").first
        if confirm:
            confirm_button = page.locator(".swal2-container .swal2-confirm")
            expect(confirm_button).to_be_visible()
            if force:
                force_checkbox = page.locator(".swal2-container .swal2-input [type='checkbox'], .swal2-container input[type='checkbox']")
                if force_checkbox.count():
                    force_checkbox.check()
            confirm_button.click(force=True)
        else:
            expect(row_locator).not_to_be_visible()

        try:
            expect(row_locator).not_to_be_visible(timeout=10000)
        except AssertionError:
            page.reload(wait_until="domcontentloaded")
            expect(page.locator(f"[data-testid='{delete_button_test_id}']").locator("xpath=ancestor::tr[1]").first).not_to_be_visible(
                timeout=20000
            )

    def get_table_row_id_by_link_text(self, page: Page, table_id: str, link_text: str) -> str:
        """Return the row id from the first matching link href inside a table."""
        item_href = self._get_table_link_locator(page, table_id, link_text).get_attribute("href") or ""
        item_id = item_href.rstrip("/").split("/")[-1]
        assert item_id, f"Expected item id for '{link_text}' in table '{table_id}'"
        return item_id

    def assert_item_in_table(self, page: Page, table_id: str, link_text: str):
        """Assert that an item appears in a table."""
        expect(self._get_table_link_locator(page, table_id, link_text)).to_be_visible()

    def assert_item_not_in_table(self, page: Page, table_id: str, link_text: str):
        """Assert that an item does not appear in a table."""
        expect(self._get_table_link_locator(page, table_id, link_text)).not_to_be_visible()

    def open_table_item(self, page: Page, table_id: str, link_text: str):
        """Open a table item via the shared table macro anchor selector."""
        self._get_table_link_locator(page, table_id, link_text).click()

    def delete_item(self, page: Page, table_id: str, link_text: str, confirm: bool = True, force: bool = False):
        """Delete a table item located by its link text and assert it is removed."""
        item_id = self.get_table_row_id_by_link_text(page, table_id, link_text)
        self.delete_table_row(page, f"action-delete-{item_id}", confirm=confirm, force=force)
        self.assert_item_not_in_table(page, table_id, link_text)

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

    def assert_dashboard_sections_visible(self, page: Page, sections: list[str]):
        """Assert dashboard sections are visible."""
        for section in sections:
            expect(page.locator("#dashboard")).to_contain_text(section)
