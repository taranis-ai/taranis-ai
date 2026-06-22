from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from playwright.async_api import Page as AsyncPage
from playwright.async_api import expect as async_expect
from playwright.sync_api import Page, expect
from tests.load.load_testing.browser_contract import (
    ANALYZE_DETAIL_READY_EVENT,
    ANALYZE_LIST_READY_EVENT,
    ANALYZE_PATH,
    ANALYZE_ROOT_TEST_ID,
    ASSESS_COUNT_TEST_ID,
    ASSESS_DETAIL_READY_EVENT,
    ASSESS_LIST_READY_EVENT,
    ASSESS_PATH,
    ASSESS_ROOT_TEST_ID,
    DASHBOARD_MARKERS,
    DASHBOARD_PATH,
    DASHBOARD_READY_EVENT,
    DASHBOARD_ROOT_SELECTOR,
    FRONTEND_LOGIN_PATH,
    LOGIN_BUTTON_TEST_ID,
    LOGIN_PASSWORD_PLACEHOLDER,
    LOGIN_READY_EVENT,
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

LOAD_MEASURED_FLOW_ATTR = "_load_measured_flow_names"


@dataclass(frozen=True)
class FrontendFlowConfig:
    username: str = "user"
    password: str = "test"
    expected_report_title: str = "Load Test Report 1"


SyncRunner = Callable[[Page, FrontendFlowConfig], None]
AsyncRunner = Callable[[AsyncPage, FrontendFlowConfig], Awaitable[None]]


@dataclass(frozen=True)
class FrontendFlowDefinition:
    name: str
    page_event_name: str
    locust_weight: int
    load_enabled: bool
    sync_runner: SyncRunner
    async_runner: AsyncRunner


FLOW_REGISTRY: dict[str, FrontendFlowDefinition] = {}


def load_measured_flow(*flow_names: str):
    """Mark a frontend Playwright test with the shared load-test flow names it covers."""

    def decorator(func):
        setattr(func, LOAD_MEASURED_FLOW_ATTR, tuple(flow_names))
        return func

    return decorator


def register_frontend_flow(
    *,
    name: str,
    page_event_name: str,
    locust_weight: int,
    sync_runner: SyncRunner,
    async_runner: AsyncRunner,
    load_enabled: bool = True,
) -> None:
    FLOW_REGISTRY[name] = FrontendFlowDefinition(
        name=name,
        page_event_name=page_event_name,
        locust_weight=locust_weight,
        load_enabled=load_enabled,
        sync_runner=sync_runner,
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
        return [flow for flow in FLOW_REGISTRY.values() if flow.load_enabled]
    return [get_flow_definition(name) for name in names]


def run_sync_frontend_flow(name: str, page: Page, config: FrontendFlowConfig) -> None:
    get_flow_definition(name).sync_runner(page, config)


async def run_async_frontend_flow(name: str, page: AsyncPage, config: FrontendFlowConfig) -> None:
    await get_flow_definition(name).async_runner(page, config)


def _sync_open_login(page: Page) -> None:
    from flask import url_for

    page.goto(url_for("base.login", _external=True))
    expect(page.get_by_placeholder(LOGIN_USERNAME_PLACEHOLDER)).to_be_visible()


async def _async_open_login(page: AsyncPage) -> None:
    await page.goto(FRONTEND_LOGIN_PATH, wait_until="domcontentloaded")
    await async_expect(page.get_by_placeholder(LOGIN_USERNAME_PLACEHOLDER)).to_be_visible()


def _sync_assert_dashboard(page: Page) -> None:
    dashboard = page.locator(DASHBOARD_ROOT_SELECTOR)
    expect(dashboard).to_be_visible()
    for marker in DASHBOARD_MARKERS:
        expect(dashboard.get_by_text(marker, exact=False)).to_be_visible()


async def _async_assert_dashboard(page: AsyncPage) -> None:
    dashboard = page.locator(DASHBOARD_ROOT_SELECTOR)
    await async_expect(dashboard).to_be_visible()
    for marker in DASHBOARD_MARKERS:
        await async_expect(dashboard.get_by_text(marker, exact=False)).to_be_visible()


def _sync_login_to_dashboard(page: Page, config: FrontendFlowConfig) -> None:
    _sync_open_login(page)
    page.get_by_placeholder(LOGIN_USERNAME_PLACEHOLDER).fill(config.username)
    page.get_by_placeholder(LOGIN_PASSWORD_PLACEHOLDER).fill(config.password)
    page.get_by_test_id(LOGIN_BUTTON_TEST_ID).click()
    _sync_assert_dashboard(page)


async def _async_login_to_dashboard(page: AsyncPage, config: FrontendFlowConfig) -> None:
    await _async_open_login(page)
    await page.get_by_placeholder(LOGIN_USERNAME_PLACEHOLDER).fill(config.username)
    await page.get_by_placeholder(LOGIN_PASSWORD_PLACEHOLDER).fill(config.password)
    await page.get_by_test_id(LOGIN_BUTTON_TEST_ID).click()
    await page.wait_for_url(f"**{DASHBOARD_PATH}", wait_until="domcontentloaded")
    await _async_assert_dashboard(page)


def get_navbar(page):
    return page.locator(NAVBAR_ROOT_SELECTOR)


def _sync_open_dashboard(page: Page) -> None:
    from flask import url_for

    page.goto(url_for("base.dashboard", _external=True))
    _sync_assert_dashboard(page)


async def _async_open_dashboard(page: AsyncPage) -> None:
    await page.goto(DASHBOARD_PATH, wait_until="domcontentloaded")
    await _async_assert_dashboard(page)


def _sync_assert_assess_list(page: Page) -> None:
    expect(page.get_by_test_id(ASSESS_ROOT_TEST_ID)).to_be_visible()
    expect(page.get_by_test_id(ASSESS_COUNT_TEST_ID)).to_be_visible()
    expect(page.get_by_role("searchbox", name="Select sources")).to_be_visible()
    expect(page.locator("[data-testid^='story-card-']").first).to_be_visible()


async def _async_assert_assess_list(page: AsyncPage) -> None:
    await async_expect(page.get_by_test_id(ASSESS_ROOT_TEST_ID)).to_be_visible()
    await async_expect(page.get_by_test_id(ASSESS_COUNT_TEST_ID)).to_be_visible()
    await async_expect(page.get_by_role("searchbox", name="Select sources")).to_be_visible()
    await async_expect(page.locator("[data-testid^='story-card-']").first).to_be_visible()


def _sync_open_assess_list(page: Page) -> None:
    from flask import url_for

    page.goto(url_for("assess.assess", _external=True))
    _sync_assert_assess_list(page)


async def _async_open_assess_list(page: AsyncPage) -> None:
    await get_navbar(page).get_by_role("link", name=USER_NAV_ASSESS_LABEL).click()
    await page.wait_for_url(f"**{ASSESS_PATH}**", wait_until="domcontentloaded")
    await _async_assert_assess_list(page)


def _sync_open_first_assess_detail(page: Page) -> None:
    first_story = page.locator("[data-testid^='story-card-']").first
    first_story.get_by_test_id(STORY_DETAIL_VIEW_TEST_ID).click()
    expect(page.get_by_test_id(STORY_DETAIL_TITLE_TEST_ID)).to_be_visible()


async def _async_open_first_assess_detail(page: AsyncPage) -> None:
    first_story = page.locator("[data-testid^='story-card-']").first
    await first_story.get_by_test_id(STORY_DETAIL_VIEW_TEST_ID).click()
    await async_expect(page.get_by_test_id(STORY_DETAIL_TITLE_TEST_ID)).to_be_visible()


def _sync_assert_analyze_list(page: Page, config: FrontendFlowConfig) -> None:
    report_table = page.get_by_test_id(REPORT_TABLE_TEST_ID)
    expect(page.get_by_test_id(ANALYZE_ROOT_TEST_ID)).to_be_visible()
    expect(page.get_by_test_id(NEW_REPORT_BUTTON_TEST_ID)).to_be_visible()
    expect(report_table).to_be_visible()
    expect(report_table.get_by_role("link", name=config.expected_report_title, exact=True)).to_be_visible()


async def _async_assert_analyze_list(page: AsyncPage, config: FrontendFlowConfig) -> None:
    report_table = page.get_by_test_id(REPORT_TABLE_TEST_ID)
    await async_expect(page.get_by_test_id(ANALYZE_ROOT_TEST_ID)).to_be_visible()
    await async_expect(page.get_by_test_id(NEW_REPORT_BUTTON_TEST_ID)).to_be_visible()
    await async_expect(report_table).to_be_visible()
    await async_expect(report_table.get_by_role("link", name=config.expected_report_title, exact=True)).to_be_visible()


def _sync_open_analyze_list(page: Page, config: FrontendFlowConfig) -> None:
    from flask import url_for

    page.goto(url_for("analyze.analyze", _external=True))
    _sync_assert_analyze_list(page, config)


async def _async_open_analyze_list(page: AsyncPage, config: FrontendFlowConfig) -> None:
    await get_navbar(page).get_by_role("link", name=USER_NAV_ANALYZE_LABEL).click()
    await page.wait_for_url(f"**{ANALYZE_PATH}**", wait_until="domcontentloaded")
    await _async_assert_analyze_list(page, config)


def _sync_open_report_detail(page: Page, config: FrontendFlowConfig) -> None:
    page.get_by_test_id(REPORT_TABLE_TEST_ID).get_by_role("link", name=config.expected_report_title, exact=True).click()
    expect(page.get_by_test_id(REPORT_STORIES_TEST_ID)).to_be_visible()
    expect(page.get_by_role("textbox", name=REPORT_TITLE_INPUT_NAME)).to_have_value(config.expected_report_title)


async def _async_open_report_detail(page: AsyncPage, config: FrontendFlowConfig) -> None:
    await page.get_by_test_id(REPORT_TABLE_TEST_ID).get_by_role("link", name=config.expected_report_title, exact=True).click()
    await async_expect(page.get_by_test_id(REPORT_STORIES_TEST_ID)).to_be_visible()
    await async_expect(page.get_by_role("textbox", name=REPORT_TITLE_INPUT_NAME)).to_have_value(config.expected_report_title)


def _sync_dashboard_flow(page: Page, config: FrontendFlowConfig) -> None:
    _sync_open_dashboard(page)


async def _async_dashboard_flow(page: AsyncPage, config: FrontendFlowConfig) -> None:
    await _async_open_dashboard(page)


def _sync_assess_list_flow(page: Page, config: FrontendFlowConfig) -> None:
    _sync_open_assess_list(page)


async def _async_assess_list_flow(page: AsyncPage, config: FrontendFlowConfig) -> None:
    await _async_open_assess_list(page)


def _sync_assess_detail_flow(page: Page, config: FrontendFlowConfig) -> None:
    _sync_open_assess_list(page)
    _sync_open_first_assess_detail(page)


async def _async_assess_detail_flow(page: AsyncPage, config: FrontendFlowConfig) -> None:
    await _async_open_assess_list(page)
    await _async_open_first_assess_detail(page)


def _sync_analyze_report_detail_flow(page: Page, config: FrontendFlowConfig) -> None:
    _sync_open_analyze_list(page, config)
    _sync_open_report_detail(page, config)


async def _async_analyze_report_detail_flow(page: AsyncPage, config: FrontendFlowConfig) -> None:
    await _async_open_analyze_list(page, config)
    await _async_open_report_detail(page, config)


register_frontend_flow(
    name=FLOW_LOGIN,
    page_event_name=LOGIN_READY_EVENT,
    locust_weight=1,
    sync_runner=_sync_login_to_dashboard,
    async_runner=_async_login_to_dashboard,
)

register_frontend_flow(
    name=FLOW_DASHBOARD,
    page_event_name=DASHBOARD_READY_EVENT,
    locust_weight=3,
    sync_runner=_sync_dashboard_flow,
    async_runner=_async_dashboard_flow,
)

register_frontend_flow(
    name=FLOW_ASSESS_LIST,
    page_event_name=ASSESS_LIST_READY_EVENT,
    locust_weight=2,
    sync_runner=_sync_assess_list_flow,
    async_runner=_async_assess_list_flow,
)

register_frontend_flow(
    name=FLOW_ASSESS_DETAIL,
    page_event_name=ASSESS_DETAIL_READY_EVENT,
    locust_weight=2,
    sync_runner=_sync_assess_detail_flow,
    async_runner=_async_assess_detail_flow,
)

register_frontend_flow(
    name=FLOW_ANALYZE_LIST,
    page_event_name=ANALYZE_LIST_READY_EVENT,
    locust_weight=2,
    sync_runner=_sync_open_analyze_list,
    async_runner=_async_open_analyze_list,
)

register_frontend_flow(
    name=FLOW_ANALYZE_REPORT_DETAIL,
    page_event_name=ANALYZE_DETAIL_READY_EVENT,
    locust_weight=2,
    sync_runner=_sync_analyze_report_detail_flow,
    async_runner=_async_analyze_report_detail_flow,
)
