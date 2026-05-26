import os
import re
from urllib.parse import urlsplit

import requests
import responses

from tests.playwright.e2e_harness import wait_for_http_ok


LOCALHOST_PASSTHRU_PATTERN = re.compile(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?(/|$)")


def normalize_and_validate_absolute_url(url: str, env_name: str) -> str:
    normalized = url.strip().rstrip("/")
    parsed = urlsplit(normalized)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError(f"{env_name} must be an absolute URL, got: {url}")
    return normalized


def external_frontend_base_url() -> str | None:
    base_url = os.getenv("TARANIS_E2E_EXTERNAL_BASE_URL", "").strip()
    if not base_url:
        return None
    return normalize_and_validate_absolute_url(base_url, "TARANIS_E2E_EXTERNAL_BASE_URL")


def external_core_api_url() -> str | None:
    core_url = os.getenv("TARANIS_E2E_EXTERNAL_CORE_URL", "").strip()
    if not core_url:
        return None
    normalized = normalize_and_validate_absolute_url(core_url, "TARANIS_E2E_EXTERNAL_CORE_URL")
    return normalized if normalized.endswith("/api") else f"{normalized}/api"


def external_auth_credentials() -> tuple[str, str]:
    return (
        os.getenv("TARANIS_E2E_EXTERNAL_AUTH_USERNAME", "admin"),
        os.getenv("TARANIS_E2E_EXTERNAL_AUTH_PASSWORD", "admin"),
    )


def external_basic_auth_credentials() -> tuple[str, str]:
    return (
        os.getenv("TARANIS_E2E_EXTERNAL_BASIC_AUTH_USERNAME", "user"),
        os.getenv("TARANIS_E2E_EXTERNAL_BASIC_AUTH_PASSWORD", "test"),
    )


def configure_external_frontend_environment() -> tuple[str, str, str] | None:
    base_url = external_frontend_base_url()
    if not base_url:
        return None

    parsed = urlsplit(base_url)
    application_root = parsed.path.rstrip("/") or "/"

    os.environ["APPLICATION_ROOT"] = application_root
    os.environ["JWT_COOKIE_SECURE"] = "False"

    return parsed.netloc, application_root, parsed.scheme


def core_host_from_api_url(core_api_url: str) -> str:
    parsed = urlsplit(core_api_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def login_to_core(core_api_url: str, username: str, password: str):
    response = requests.post(
        f"{core_api_url}/auth/login",
        json={"username": username, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    return response


def allow_requests_passthru(url: str | None = None) -> None:
    responses.add_passthru(LOCALHOST_PASSTHRU_PATTERN)
    if not url:
        return

    parsed = urlsplit(url)
    if parsed.scheme and parsed.netloc:
        responses.add_passthru(f"{parsed.scheme}://{parsed.netloc}")


def wait_for_server_to_be_alive(url: str, timeout_seconds: int = 10, poll_interval: float = 0.5) -> bool:
    allow_requests_passthru(url)
    wait_for_http_ok(url, timeout_seconds=timeout_seconds, poll_interval=poll_interval)
    return True
