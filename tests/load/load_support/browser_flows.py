import os

from locust import between, task
from locust_plugins.users.playwright import PlaywrightUser, event, pw
from playwright.async_api import expect

from testsupport.load_testing.browser_contract import (
    ANALYZE_PATH,
    ANALYZE_READY_EVENT,
    ANALYZE_ROOT_TEST_ID,
    ASSESS_COUNT_TEST_ID,
    ASSESS_PATH,
    ASSESS_READY_EVENT,
    ASSESS_ROOT_TEST_ID,
    DASHBOARD_PATH,
    DASHBOARD_MARKERS,
    DASHBOARD_READY_EVENT,
    DASHBOARD_ROOT_SELECTOR,
    FRONTEND_LOGIN_PATH,
    LOGIN_DASHBOARD_READY_EVENT,
    LOGIN_BUTTON_TEST_ID,
    LOGIN_PASSWORD_PLACEHOLDER,
    LOGIN_USERNAME_PLACEHOLDER,
    NAVBAR_ROOT_SELECTOR,
    NEW_REPORT_BUTTON_TEST_ID,
    PAGE_REQUEST_TYPE,
    REPORT_TABLE_TEST_ID,
    USER_NAV_ANALYZE_LABEL,
    USER_NAV_ASSESS_LABEL,
)


EXPECTED_REPORT_TITLE = os.getenv("TARANIS_EXPECTED_REPORT_TITLE", "Load Test Report 1")


async def open_login(page) -> None:
    await page.goto(FRONTEND_LOGIN_PATH, wait_until="domcontentloaded")
    await expect(page.get_by_placeholder(LOGIN_USERNAME_PLACEHOLDER)).to_be_visible()


async def login_and_land_on_dashboard(page, username: str, password: str) -> None:
    await open_login(page)
    await page.get_by_placeholder(LOGIN_USERNAME_PLACEHOLDER).fill(username)
    await page.get_by_placeholder(LOGIN_PASSWORD_PLACEHOLDER).fill(password)
    await page.get_by_test_id(LOGIN_BUTTON_TEST_ID).click()
    await page.wait_for_url("**/frontend/", wait_until="domcontentloaded")
    await assert_dashboard(page)


async def assert_dashboard(page) -> None:
    dashboard = page.locator(DASHBOARD_ROOT_SELECTOR)
    await expect(dashboard).to_be_visible()
    for marker in DASHBOARD_MARKERS:
        await expect(dashboard.get_by_text(marker, exact=False)).to_be_visible()


def navbar(page):
    return page.locator(NAVBAR_ROOT_SELECTOR)


async def assert_assess(page) -> None:
    await expect(page.get_by_test_id(ASSESS_ROOT_TEST_ID)).to_be_visible()
    await expect(page.get_by_test_id(ASSESS_COUNT_TEST_ID)).to_be_visible()
    await expect(page.locator("[data-testid^='story-card-']").first).to_be_visible()


async def assert_analyze(page) -> None:
    await expect(page.get_by_test_id(ANALYZE_ROOT_TEST_ID)).to_be_visible()
    await expect(page.get_by_test_id(NEW_REPORT_BUTTON_TEST_ID)).to_be_visible()
    await expect(page.get_by_test_id(REPORT_TABLE_TEST_ID)).to_be_visible()
    await expect(page.get_by_text(EXPECTED_REPORT_TITLE, exact=False)).to_be_visible()


async def login_with_page_ready_metric(user: PlaywrightUser, page, username: str, password: str) -> None:
    await open_login(page)
    await page.get_by_placeholder(LOGIN_USERNAME_PLACEHOLDER).fill(username)
    await page.get_by_placeholder(LOGIN_PASSWORD_PLACEHOLDER).fill(password)
    async with event(user, LOGIN_DASHBOARD_READY_EVENT, request_type=PAGE_REQUEST_TYPE):
        await page.get_by_test_id(LOGIN_BUTTON_TEST_ID).click()
        await page.wait_for_url("**/frontend/", wait_until="domcontentloaded")
        await assert_dashboard(page)


async def load_dashboard_ready(user: PlaywrightUser, page) -> None:
    async with event(user, DASHBOARD_READY_EVENT, request_type=PAGE_REQUEST_TYPE):
        await page.goto(DASHBOARD_PATH, wait_until="domcontentloaded")
        await assert_dashboard(page)


async def load_assess_ready(user: PlaywrightUser, page) -> None:
    async with event(user, ASSESS_READY_EVENT, request_type=PAGE_REQUEST_TYPE):
        await navbar(page).get_by_role("link", name=USER_NAV_ASSESS_LABEL).click()
        await page.wait_for_url(f"**{ASSESS_PATH}**", wait_until="domcontentloaded")
        await assert_assess(page)


async def load_analyze_ready(user: PlaywrightUser, page) -> None:
    async with event(user, ANALYZE_READY_EVENT, request_type=PAGE_REQUEST_TYPE):
        await navbar(page).get_by_role("link", name=USER_NAV_ANALYZE_LABEL).click()
        await page.wait_for_url(f"**{ANALYZE_PATH}**", wait_until="domcontentloaded")
        await assert_analyze(page)


class FrontendBrowserUser(PlaywrightUser):
    host = os.getenv("TARGET_HOST", "http://ingress:8080")
    wait_time = between(1, 3)
    username = os.getenv("TARANIS_LOAD_USERNAME", "user")
    password = os.getenv("TARANIS_LOAD_PASSWORD", "test")

    @task(1)
    @pw
    async def login_flow(self, page):
        await login_with_page_ready_metric(self, page, self.username, self.password)

    @task(3)
    @pw
    async def dashboard_flow(self, page):
        await login_and_land_on_dashboard(page, self.username, self.password)
        await load_dashboard_ready(self, page)

    @task(2)
    @pw
    async def assess_flow(self, page):
        await login_and_land_on_dashboard(page, self.username, self.password)
        await load_assess_ready(self, page)

    @task(2)
    @pw
    async def analyze_flow(self, page):
        await login_and_land_on_dashboard(page, self.username, self.password)
        await load_analyze_ready(self, page)
