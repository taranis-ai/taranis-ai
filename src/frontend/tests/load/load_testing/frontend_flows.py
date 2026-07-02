from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from playwright.async_api import Page, expect
from tests.load.load_testing.browser_contract import (
    ANALYZE_PATH,
    ANALYZE_ROOT_TEST_ID,
    ASSESS_COUNT_TEST_ID,
    ASSESS_PATH,
    ASSESS_ROOT_TEST_ID,
    DASHBOARD_MARKERS,
    DASHBOARD_PATH,
    DASHBOARD_ROOT_SELECTOR,
    FRONTEND_LOGIN_PATH,
    LOGIN_BUTTON_TEST_ID,
    LOGIN_PASSWORD_PLACEHOLDER,
    LOGIN_USERNAME_PLACEHOLDER,
    NAVBAR_ROOT_SELECTOR,
    NEW_REPORT_BUTTON_TEST_ID,
    REPORT_STORIES_TEST_ID,
    REPORT_TABLE_TEST_ID,
    REPORT_TITLE_INPUT_NAME,
    STORY_DETAIL_TITLE_TEST_ID,
    STORY_DETAIL_VIEW_TEST_ID,
    USER_NAV_ANALYZE_LABEL,
    USER_NAV_ASSESS_LABEL,
)

FLOW_LOGIN = "login"
FLOW_DASHBOARD = "dashboard"
FLOW_ASSESS_LIST = "assess_list"
FLOW_ASSESS_DETAIL = "assess_detail"
FLOW_ANALYZE_LIST = "analyze_list"
FLOW_ANALYZE_REPORT_DETAIL = "analyze_report_detail"


@dataclass(frozen=True)
class FrontendFlowConfig:
    username: str = "user"
    password: str = "test"
    expected_report_title: str = "Load Test Report 1"


AsyncRunner = Callable[[Page, FrontendFlowConfig], Awaitable[None]]


@dataclass(frozen=True)
class FrontendFlowDefinition:
    name: str
    locust_weight: int
    async_runner: AsyncRunner


FLOW_REGISTRY: dict[str, FrontendFlowDefinition] = {}


def register_frontend_flow(
    *,
    name: str,
    locust_weight: int,
    async_runner: AsyncRunner,
) -> None:
    FLOW_REGISTRY[name] = FrontendFlowDefinition(
        name=name,
        locust_weight=locust_weight,
        async_runner=async_runner,
    )


def get_flow_definition(name: str) -> FrontendFlowDefinition:
    try:
        return FLOW_REGISTRY[name]
    except KeyError as exc:
        available = ", ".join(sorted(FLOW_REGISTRY))
        raise ValueError(f"Unknown frontend flow '{name}'. Available flows: {available}") from exc


def get_load_enabled_flows(names: list[str] | None = None) -> list[FrontendFlowDefinition]:
    if names is None:
        return list(FLOW_REGISTRY.values())
    return [get_flow_definition(name) for name in names]


def get_navbar(page: Page):
    return page.locator(NAVBAR_ROOT_SELECTOR)


async def _open_login(page: Page) -> None:
    await page.goto(FRONTEND_LOGIN_PATH, wait_until="domcontentloaded")
    await expect(page.get_by_placeholder(LOGIN_USERNAME_PLACEHOLDER)).to_be_visible()


async def _assert_dashboard(page: Page) -> None:
    dashboard = page.locator(DASHBOARD_ROOT_SELECTOR)
    await expect(dashboard).to_be_visible()
    for marker in DASHBOARD_MARKERS:
        await expect(dashboard.get_by_text(marker, exact=False)).to_be_visible()


async def _login_to_dashboard(page: Page, config: FrontendFlowConfig) -> None:
    await _open_login(page)
    await page.get_by_placeholder(LOGIN_USERNAME_PLACEHOLDER).fill(config.username)
    await page.get_by_placeholder(LOGIN_PASSWORD_PLACEHOLDER).fill(config.password)
    await page.get_by_test_id(LOGIN_BUTTON_TEST_ID).click()
    await page.wait_for_url(f"**{DASHBOARD_PATH}", wait_until="domcontentloaded")
    await _assert_dashboard(page)


async def _open_dashboard(page: Page, config: FrontendFlowConfig) -> None:
    await page.goto(DASHBOARD_PATH, wait_until="domcontentloaded")
    await _assert_dashboard(page)


async def _assert_assess_list(page: Page) -> None:
    await expect(page.get_by_test_id(ASSESS_ROOT_TEST_ID)).to_be_visible()
    await expect(page.get_by_test_id(ASSESS_COUNT_TEST_ID)).to_be_visible()
    await expect(page.get_by_role("searchbox", name="Select sources")).to_be_visible()
    await expect(page.locator("[data-testid^='story-card-']").first).to_be_visible()


async def _open_assess_list(page: Page, config: FrontendFlowConfig) -> None:
    await get_navbar(page).get_by_role("link", name=USER_NAV_ASSESS_LABEL).click()
    await page.wait_for_url(f"**{ASSESS_PATH}**", wait_until="domcontentloaded")
    await _assert_assess_list(page)


async def _open_first_assess_detail(page: Page) -> None:
    first_story = page.locator("[data-testid^='story-card-']").first
    await first_story.get_by_test_id(STORY_DETAIL_VIEW_TEST_ID).click()
    await expect(page.get_by_test_id(STORY_DETAIL_TITLE_TEST_ID)).to_be_visible()


async def _assess_detail_flow(page: Page, config: FrontendFlowConfig) -> None:
    await _open_assess_list(page, config)
    await _open_first_assess_detail(page)


async def _assert_analyze_list(page: Page, config: FrontendFlowConfig) -> None:
    report_table = page.get_by_test_id(REPORT_TABLE_TEST_ID)
    await expect(page.get_by_test_id(ANALYZE_ROOT_TEST_ID)).to_be_visible()
    await expect(page.get_by_test_id(NEW_REPORT_BUTTON_TEST_ID)).to_be_visible()
    await expect(report_table).to_be_visible()
    await expect(report_table.get_by_role("link", name=config.expected_report_title, exact=True)).to_be_visible()


async def _open_analyze_list(page: Page, config: FrontendFlowConfig) -> None:
    await get_navbar(page).get_by_role("link", name=USER_NAV_ANALYZE_LABEL).click()
    await page.wait_for_url(f"**{ANALYZE_PATH}**", wait_until="domcontentloaded")
    await _assert_analyze_list(page, config)


async def _open_report_detail(page: Page, config: FrontendFlowConfig) -> None:
    await page.get_by_test_id(REPORT_TABLE_TEST_ID).get_by_role("link", name=config.expected_report_title, exact=True).click()
    await expect(page.get_by_test_id(REPORT_STORIES_TEST_ID)).to_be_visible()
    await expect(page.get_by_role("textbox", name=REPORT_TITLE_INPUT_NAME)).to_have_value(config.expected_report_title)


async def _analyze_report_detail_flow(page: Page, config: FrontendFlowConfig) -> None:
    await _open_analyze_list(page, config)
    await _open_report_detail(page, config)


register_frontend_flow(
    name=FLOW_LOGIN,
    locust_weight=1,
    async_runner=_login_to_dashboard,
)

register_frontend_flow(
    name=FLOW_DASHBOARD,
    locust_weight=3,
    async_runner=_open_dashboard,
)

register_frontend_flow(
    name=FLOW_ASSESS_LIST,
    locust_weight=2,
    async_runner=_open_assess_list,
)

register_frontend_flow(
    name=FLOW_ASSESS_DETAIL,
    locust_weight=2,
    async_runner=_assess_detail_flow,
)

register_frontend_flow(
    name=FLOW_ANALYZE_LIST,
    locust_weight=2,
    async_runner=_open_analyze_list,
)

register_frontend_flow(
    name=FLOW_ANALYZE_REPORT_DETAIL,
    locust_weight=2,
    async_runner=_analyze_report_detail_flow,
)
