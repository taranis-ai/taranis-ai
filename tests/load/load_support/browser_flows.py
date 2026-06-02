import os

from locust import between, task
from playwright.async_api import expect

from load_support.playwright_stats import event, pw
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
from testsupport.load_testing.frontend_flows import (
    FrontendFlowConfig,
    get_load_enabled_flows,
)
from locust_plugins.users.playwright import PlaywrightUser


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


async def ensure_logged_in(page, username: str, password: str) -> None:
    if "/frontend/" in page.url and "login" not in page.url:
        return
    await login_and_land_on_dashboard(page, username, password)


async def login_if_needed(
    user: PlaywrightUser,
    page,
    username: str,
    password: str,
    *,
    record_login_metric: bool,
) -> bool:
    if "/frontend/" in page.url and "login" not in page.url:
        return False
    if record_login_metric:
        await login_with_page_ready_metric(user, page, username, password)
    else:
        await login_and_land_on_dashboard(page, username, password)
    return True


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
        did_login = await login_if_needed(
            self,
            page,
            self.username,
            self.password,
            record_login_metric=True,
        )
        if not did_login:
            await page.goto(DASHBOARD_PATH, wait_until="domcontentloaded")
            await assert_dashboard(page)

    @task(3)
    @pw
    async def dashboard_flow(self, page):
        await login_if_needed(
            self,
            page,
            self.username,
            self.password,
            record_login_metric=False,
        )
        await load_dashboard_ready(self, page)

    @task(2)
    @pw
    async def assess_flow(self, page):
        await login_if_needed(
            self,
            page,
            self.username,
            self.password,
            record_login_metric=False,
        )
        await load_assess_ready(self, page)

    @task(2)
    @pw
    async def analyze_flow(self, page):
        await login_if_needed(
            self,
            page,
            self.username,
            self.password,
            record_login_metric=False,
        )
        await load_analyze_ready(self, page)


def parse_selected_flow_names(raw_flow_names: str | None) -> list[str] | None:
    if raw_flow_names is None:
        return None
    names = [name.strip() for name in raw_flow_names.split(",") if name.strip()]
    if not names:
        raise ValueError("TARANIS_LOAD_FLOWS was provided but no valid flow names were found")
    return names


def build_selected_e2e_flow_user_class() -> type[PlaywrightUser]:
    selected_names = parse_selected_flow_names(os.getenv("TARANIS_LOAD_FLOWS"))
    selected_flows = get_load_enabled_flows(selected_names)

    async def _run_selected_flow(self, page, flow_definition):
        config = FrontendFlowConfig(
            username=self.username,
            password=self.password,
            expected_report_title=self.expected_report_title,
        )
        if flow_definition.name != "login":
            await ensure_logged_in(page, config.username, config.password)
        async with event(self, flow_definition.page_event_name, request_type=PAGE_REQUEST_TYPE):
            await flow_definition.async_runner(page, config)

    attributes = {
        "host": os.getenv("TARGET_HOST", "http://ingress:8080"),
        "wait_time": between(1, 3),
        "username": os.getenv("TARANIS_LOAD_USERNAME", "user"),
        "password": os.getenv("TARANIS_LOAD_PASSWORD", "test"),
        "expected_report_title": os.getenv(
            "TARANIS_EXPECTED_REPORT_TITLE", "Load Test Report 1"
        ),
    }

    for flow_definition in selected_flows:
        async def flow_task(self, page, flow_definition=flow_definition):
            await _run_selected_flow(self, page, flow_definition)

        attributes[f"{flow_definition.name}_flow"] = task(flow_definition.locust_weight)(
            pw(flow_task)
        )

    return type("FrontendSelectedE2EFlowUser", (PlaywrightUser,), attributes)
