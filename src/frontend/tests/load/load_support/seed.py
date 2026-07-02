import os
from copy import deepcopy
from typing import Any

import requests
from tests.load.load_testing.seed_data import (
    DEFAULT_REPORT_COUNT,
    DEFAULT_REPORT_TYPE_COUNT,
    DEFAULT_SOURCE_COUNT,
    DEFAULT_STORY_COUNT,
    DEFAULT_STORY_SOURCE_ID,
    LOAD_TEST_REPORT_TITLE_PREFIX,
    LOAD_TEST_REPORT_TYPE_DEFINITION,
    LOAD_TEST_REPORT_TYPE_TITLE,
    build_fake_source_payload,
    build_report_payload,
    build_report_type_titles,
    build_source_ids,
    load_story_seed_payloads,
)

REQUEST_TIMEOUT = 30
USER_PRODUCT_OVERVIEW_TASK_ID = "user_product_overview_v1"
ONBOARDING_COMPLETED_STATUS = "completed"


def require_env(name: str, default: str | None = None) -> str:
    if value := os.getenv(name, default):
        return value
    else:
        raise RuntimeError(f"Missing required environment variable: {name}")


def require_positive_int(name: str, default: int) -> int:
    raw_value = require_env(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer, got {raw_value!r}") from exc
    if value < 1:
        raise RuntimeError(f"Environment variable {name} must be at least 1, got {value}")
    return value


def ensure_ok(response: requests.Response, context: str) -> dict[str, Any]:
    if response.ok:
        return response.json() if response.content else {}
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    raise RuntimeError(f"{context} failed with status {response.status_code}: {payload}")


def login_session(core_api_url: str, username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{core_api_url}/auth/login",
        json={"username": username, "password": password},
        timeout=REQUEST_TIMEOUT,
    )
    payload = ensure_ok(response, f"{username} login")
    access_token = payload.get("access_token")
    if not access_token:
        raise RuntimeError(f"{username} login did not return an access token: {payload}")
    session.headers.update({"Authorization": f"Bearer {access_token}"})
    return session


def complete_user_onboarding(core_api_url: str, username: str, password: str) -> None:
    session = login_session(core_api_url, username, password)
    response = session.post(
        f"{core_api_url}/users/profile",
        json={"onboarding_tasks": {USER_PRODUCT_OVERVIEW_TASK_ID: ONBOARDING_COMPLETED_STATUS}},
        timeout=REQUEST_TIMEOUT,
    )
    ensure_ok(response, "complete user onboarding")


def ensure_osint_sources(session: requests.Session, core_api_url: str, source_ids: list[str]) -> list[str]:
    response = session.get(
        f"{core_api_url}/config/osint-sources",
        params={"fetch_all": "true"},
        timeout=REQUEST_TIMEOUT,
    )
    payload = ensure_ok(response, "fetch osint sources")
    existing_ids = {str(item.get("id")) for item in payload.get("items", [])}

    ensured_ids: list[str] = []
    for index, source_id in enumerate(source_ids, start=1):
        if source_id not in existing_ids:
            create_response = session.post(
                f"{core_api_url}/config/osint-sources",
                json=build_fake_source_payload(source_id, index=index),
                timeout=REQUEST_TIMEOUT,
            )
            ensure_ok(create_response, f"create osint source {source_id}")
        ensured_ids.append(source_id)
    return ensured_ids


def ensure_report_types(session: requests.Session, core_api_url: str, titles: list[str]) -> list[str]:
    response = session.get(
        f"{core_api_url}/config/report-item-types",
        params={"fetch_all": "true"},
        timeout=REQUEST_TIMEOUT,
    )
    payload = ensure_ok(response, "fetch report item types")
    existing_by_title = {
        str(item.get("title")): str(item.get("id"))
        for item in payload.get("items", [])
        if item.get("title") is not None and item.get("id") is not None
    }

    report_type_ids: list[str] = []
    for title in titles:
        existing_id = existing_by_title.get(title)
        if existing_id is not None:
            report_type_ids.append(existing_id)
            continue

        report_type_definition = deepcopy(LOAD_TEST_REPORT_TYPE_DEFINITION)
        report_type_definition["title"] = title
        create_response = session.post(
            f"{core_api_url}/config/report-item-types",
            json=report_type_definition,
            timeout=REQUEST_TIMEOUT,
        )
        create_payload = ensure_ok(create_response, "create load test report item type")
        report_type_id = create_payload.get("id")
        if report_type_id is None:
            raise RuntimeError(f"Load test report item type was created without an id: {create_payload}")
        report_type_ids.append(str(report_type_id))
    return report_type_ids


def seed_stories(core_api_url: str, api_key: str, source_ids: list[str], story_count: int) -> list[str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    story_ids: list[str] = []
    for story_payload in load_story_seed_payloads(source_ids, story_count):
        response = requests.post(
            f"{core_api_url}/worker/stories",
            json=story_payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        ensure_ok(response, f"seed story {story_payload['id']}")
        story_ids.append(story_payload["id"])
    return story_ids


def seed_reports(
    session: requests.Session,
    core_api_url: str,
    report_type_ids: list[str],
    story_ids: list[str],
    title_prefix: str,
    report_count: int,
) -> list[str]:
    report_ids: list[str] = []
    story_count = len(story_ids)
    for index in range(1, report_count + 1):
        story_start = (index - 1) % story_count
        selected_story_ids = [
            story_ids[story_start],
            story_ids[(story_start + 1) % story_count],
        ]
        payload = build_report_payload(
            story_ids=selected_story_ids,
            report_type_id=report_type_ids[(index - 1) % len(report_type_ids)],
            title=f"{title_prefix} {index}",
        )
        response = session.post(
            f"{core_api_url}/analyze/report-items",
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        create_payload = ensure_ok(response, f"seed report {payload['id']}")
        report_ids.append(create_payload.get("id", payload["id"]))
    return report_ids


def main() -> int:
    core_api_url = require_env("CORE_API_URL", "http://core:8080/api")
    admin_username = require_env("ADMIN_USERNAME", "admin")
    admin_password = require_env("ADMIN_PASSWORD", "admin")
    load_username = require_env("LOAD_USERNAME", "user")
    load_password = require_env("LOAD_PASSWORD", "test")
    api_key = require_env("API_KEY")
    source_id = require_env("SEED_STORY_SOURCE_ID", DEFAULT_STORY_SOURCE_ID)
    report_type_title = require_env("SEED_REPORT_TYPE_TITLE", LOAD_TEST_REPORT_TYPE_TITLE)
    report_title_prefix = require_env("SEED_REPORT_TITLE_PREFIX", LOAD_TEST_REPORT_TITLE_PREFIX)
    source_count = require_positive_int("SEED_SOURCE_COUNT", DEFAULT_SOURCE_COUNT)
    story_count = require_positive_int("SEED_STORY_COUNT", DEFAULT_STORY_COUNT)
    report_type_count = require_positive_int("SEED_REPORT_TYPE_COUNT", DEFAULT_REPORT_TYPE_COUNT)
    report_count = require_positive_int("SEED_REPORT_COUNT", DEFAULT_REPORT_COUNT)

    session = login_session(core_api_url, admin_username, admin_password)
    source_ids = ensure_osint_sources(
        session,
        core_api_url,
        build_source_ids(source_id, source_count),
    )
    report_type_ids = ensure_report_types(
        session,
        core_api_url,
        build_report_type_titles(report_type_title, report_type_count),
    )
    story_ids = seed_stories(core_api_url, api_key, source_ids, story_count)
    report_ids = seed_reports(
        session,
        core_api_url,
        report_type_ids,
        story_ids,
        report_title_prefix,
        report_count,
    )
    complete_user_onboarding(core_api_url, load_username, load_password)

    print(
        {
            "seeded_source_count": len(source_ids),
            "seeded_story_count": len(story_ids),
            "seeded_report_type_count": len(report_type_ids),
            "seeded_report_count": len(report_ids),
            "report_type_id": report_type_ids[0],
            "expected_report_title": f"{report_title_prefix} {report_count}",
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
