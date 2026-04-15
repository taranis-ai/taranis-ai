import os
from copy import deepcopy
from typing import Any

import requests

from testsupport.load_testing.seed_data import (
    DEFAULT_STORY_SOURCE_ID,
    LOAD_TEST_REPORT_TITLE_PREFIX,
    LOAD_TEST_REPORT_TYPE_DEFINITION,
    LOAD_TEST_REPORT_TYPE_TITLE,
    build_fake_source_payload,
    build_report_payload,
    load_story_seed_payloads,
)


REQUEST_TIMEOUT = 30


def require_env(name: str, default: str | None = None) -> str:
    if value := os.getenv(name, default):
        return value
    else:
        raise RuntimeError(f"Missing required environment variable: {name}")


def ensure_ok(response: requests.Response, context: str) -> dict[str, Any]:
    if response.ok:
        return response.json() if response.content else {}
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    raise RuntimeError(
        f"{context} failed with status {response.status_code}: {payload}"
    )


def login_session(core_api_url: str, username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{core_api_url}/auth/login",
        json={"username": username, "password": password},
        timeout=REQUEST_TIMEOUT,
    )
    payload = ensure_ok(response, "admin login")
    access_token = payload.get("access_token")
    if not access_token:
        raise RuntimeError(f"Admin login did not return an access token: {payload}")
    session.headers.update({"Authorization": f"Bearer {access_token}"})
    return session


def ensure_osint_source(
    session: requests.Session, core_api_url: str, source_id: str
) -> None:
    response = session.get(
        f"{core_api_url}/config/osint-sources",
        params={"search": source_id, "fetch_all": "true"},
        timeout=REQUEST_TIMEOUT,
    )
    payload = ensure_ok(response, "fetch osint sources")
    for item in payload.get("items", []):
        if str(item.get("id")) == source_id:
            return

    create_response = session.post(
        f"{core_api_url}/config/osint-sources",
        json=build_fake_source_payload(source_id),
        timeout=REQUEST_TIMEOUT,
    )
    ensure_ok(create_response, f"create osint source {source_id}")


def ensure_report_type(session: requests.Session, core_api_url: str, title: str) -> int:
    response = session.get(
        f"{core_api_url}/config/report-item-types",
        params={"search": title, "fetch_all": "true"},
        timeout=REQUEST_TIMEOUT,
    )
    payload = ensure_ok(response, "fetch report item types")
    for item in payload.get("items", []):
        if item.get("title") == title:
            return int(item["id"])

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
        raise RuntimeError(
            f"Load test report item type was created without an id: {create_payload}"
        )
    return int(report_type_id)


def seed_stories(core_api_url: str, api_key: str, source_id: str) -> list[str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    story_ids: list[str] = []
    for story_payload in load_story_seed_payloads(source_id):
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
    report_type_id: int,
    story_ids: list[str],
    title_prefix: str,
) -> list[str]:
    report_ids: list[str] = []
    for index in range(1, 4):
        payload = build_report_payload(
            story_ids=story_ids[index - 1 : index + 1],
            report_type_id=report_type_id,
            title=f"{title_prefix} {index}",
            report_id=f"load-test-report-{index}",
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
    api_key = require_env("API_KEY")
    source_id = require_env("SEED_STORY_SOURCE_ID", DEFAULT_STORY_SOURCE_ID)
    report_type_title = require_env(
        "SEED_REPORT_TYPE_TITLE", LOAD_TEST_REPORT_TYPE_TITLE
    )
    report_title_prefix = require_env(
        "SEED_REPORT_TITLE_PREFIX", LOAD_TEST_REPORT_TITLE_PREFIX
    )

    session = login_session(core_api_url, admin_username, admin_password)
    ensure_osint_source(session, core_api_url, source_id)
    report_type_id = ensure_report_type(session, core_api_url, report_type_title)
    story_ids = seed_stories(core_api_url, api_key, source_id)
    report_ids = seed_reports(
        session, core_api_url, report_type_id, story_ids, report_title_prefix
    )

    print(
        {
            "seeded_story_count": len(story_ids),
            "seeded_report_count": len(report_ids),
            "report_type_id": report_type_id,
            "expected_report_title": f"{report_title_prefix} 1",
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
