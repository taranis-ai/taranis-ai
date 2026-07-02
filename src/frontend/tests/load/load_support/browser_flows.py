# pyright: reportMissingImports=false

import os

from locust import between, task
from locust_plugins.users.playwright import PlaywrightUser, pw
from tests.load.load_testing.frontend_flows import (
    FLOW_LOGIN,
    FrontendFlowConfig,
    get_flow_definition,
    get_load_enabled_flows,
)


async def ensure_logged_in(page, config: FrontendFlowConfig) -> None:
    if "/frontend/" in page.url and "login" not in page.url:
        return
    await get_flow_definition(FLOW_LOGIN).async_runner(page, config)


def parse_selected_flow_names(raw_flow_names: str | None) -> list[str] | None:
    if raw_flow_names is None or raw_flow_names == "":
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
        if flow_definition.name != FLOW_LOGIN:
            await ensure_logged_in(page, config)
        await flow_definition.async_runner(page, config)

    attributes = {
        "host": os.getenv("TARGET_HOST", "http://ingress:8080"),
        "wait_time": between(1, 3),
        "username": os.getenv("TARANIS_LOAD_USERNAME", "user"),
        "password": os.getenv("TARANIS_LOAD_PASSWORD", "test"),
        "expected_report_title": os.getenv("TARANIS_EXPECTED_REPORT_TITLE", "Load Test Report 1"),
    }

    for flow_definition in selected_flows:

        async def flow_task(self, page, flow_definition=flow_definition):
            await _run_selected_flow(self, page, flow_definition)

        flow_task.__name__ = f"{flow_definition.name}_flow"
        attributes[f"{flow_definition.name}_flow"] = task(flow_definition.locust_weight)(pw(flow_task))

    return type("FrontendSelectedE2EFlowUser", (PlaywrightUser,), attributes)
