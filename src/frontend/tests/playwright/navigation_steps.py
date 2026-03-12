from playwright.sync_api import Page, expect
from playwright_helpers import PlaywrightHelpers


def go_to_dashboard(helpers: PlaywrightHelpers, page: Page) -> None:
    helpers.highlight_element(page.get_by_role("link", name="Dashboard"))
    page.get_by_role("link", name="Dashboard").click()
    expect(page.locator("#dashboard")).to_be_visible()


def go_to_assess(helpers: PlaywrightHelpers, page: Page) -> None:
    helpers.highlight_element(page.get_by_role("link", name="Assess").first)
    page.get_by_role("link", name="Assess").first.click()
    page.wait_for_url("**/assess**", wait_until="domcontentloaded")


def go_to_analyze(helpers: PlaywrightHelpers, page: Page) -> None:
    helpers.highlight_element(page.get_by_role("link", name="Analyze").first)
    page.get_by_role("link", name="Analyze").first.click()
    page.wait_for_url("**/analyze**", wait_until="domcontentloaded")


def go_to_publish(helpers: PlaywrightHelpers, page: Page) -> None:
    helpers.highlight_element(page.get_by_role("link", name="Publish").first)
    page.get_by_role("link", name="Publish").first.click()
    page.wait_for_url("**/publish**", wait_until="domcontentloaded")


def go_to_administration(helpers: PlaywrightHelpers, page: Page) -> None:
    helpers.highlight_element(page.get_by_role("link", name="Administration"))
    page.get_by_role("link", name="Administration").click()
    expect(page.get_by_role("link", name="Taranis AI Logo")).to_be_visible()


def go_to_user_settings(helpers: PlaywrightHelpers, page: Page) -> None:
    helpers.highlight_element(page.get_by_role("list").get_by_role("button"))
    page.get_by_role("list").get_by_role("button").click()
    expect(page.get_by_role("link", name="User Settings")).to_be_visible()
    helpers.highlight_element(page.get_by_role("link", name="User Settings"))
    page.get_by_role("link", name="User Settings").click()
    expect(page.get_by_text("User", exact=True)).to_be_visible()
