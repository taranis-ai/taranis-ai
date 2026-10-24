"""Live admin-UI evidence for the named OrcaRouter provider.

Run with the repository test runner from ``src/core``:

    uv run pytest tests/unit/test_orcarouter_gui_evidence.py -q

The test starts disposable Core and frontend instances (SQLite, queues and
caches disabled), signs in with the seeded development administrator, creates a
real OrcaRouter endpoint with the key from ``ORCAROUTER_API_KEY``, and captures
the API-key entry and the live model dropdown with headless Chromium. It never
renders the key: the saved key is held server-side, and the API-key screenshot
uses a placeholder value.

The generated manifest and screenshots are written to ``orca-evidence/``.
"""

import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
import requests
from playwright.sync_api import expect, sync_playwright


REPO_ROOT = Path(__file__).resolve().parents[4]
EVIDENCE_DIR = REPO_ROOT / "orca-evidence"
CORE_DIR = REPO_ROOT / "src" / "core"
FRONTEND_DIR = REPO_ROOT / "src" / "frontend"
CORE_PORT = 5800
FRONTEND_PORT = 5801
FRONTEND_ROOT = "/frontend"
CORE_URL = f"http://127.0.0.1:{CORE_PORT}"
FRONTEND_URL = f"http://127.0.0.1:{FRONTEND_PORT}{FRONTEND_ROOT}"
CHROMIUM = "/usr/bin/chromium"
API_KEY = os.environ.get("ORCAROUTER_API_KEY", "")
PLACEHOLDER_KEY = "sk-orca-evidence-placeholder"

pytestmark = pytest.mark.skipif(
    not API_KEY,
    reason="Live OrcaRouter credentials are not configured",
)


def _wait_for(url: str, timeout: float = 120) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = requests.get(url, timeout=2, allow_redirects=False)
            if response.status_code < 500:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"Service did not start: {url}")


def _server_env(database: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database}",
            "QUEUE_ENABLED": "false",
            "DISABLE_SCHEDULER": "true",
            "REALTIME_ENABLED": "false",
            "DEBUG": "false",
            "PRE_SEED_SETTINGS": json.dumps({"onboarding_enabled": False}),
        }
    )
    return env


def _start(core_python: Path, frontend_python: Path, database: Path, log_dir: Path):
    core_log = (log_dir / "core.log").open("wb")
    core = subprocess.Popen(
        [str(core_python), "-m", "flask", "--app", "app", "run", "--host", "127.0.0.1", "--port", str(CORE_PORT), "--no-reload"],
        cwd=CORE_DIR,
        env=_server_env(database),
        stdout=core_log,
        stderr=subprocess.STDOUT,
    )
    _wait_for(f"{CORE_URL}/api/isalive")
    frontend_env = _server_env(database)
    frontend_env.update(
        {
            "TARANIS_CORE_URL": f"{CORE_URL}/api",
            "CORE_API_KEY": "supersecret",
            "CACHE_ENABLED": "false",
            "APPLICATION_ROOT": FRONTEND_ROOT,
        }
    )
    frontend_log = (log_dir / "frontend.log").open("wb")
    frontend = subprocess.Popen(
        [str(frontend_python), "-m", "flask", "--app", "app", "run", "--host", "127.0.0.1", "--port", str(FRONTEND_PORT), "--no-reload"],
        cwd=FRONTEND_DIR,
        env=frontend_env,
        stdout=frontend_log,
        stderr=subprocess.STDOUT,
    )
    _wait_for(f"{FRONTEND_URL}/login")
    return (core, core_log), (frontend, frontend_log)


def _stop(servers) -> None:
    for process, log in servers:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()


def _tail(path: Path) -> str:
    if not path.exists():
        return ""
    text = path.read_text(errors="replace")[-4000:]
    if API_KEY:
        text = text.replace(API_KEY, "[redacted]")
    return text


def _png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"Not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact(kind: str, filename: str, ui: dict) -> dict:
    return {
        "kind": kind,
        "path": filename,
        "sha256": _sha256(EVIDENCE_DIR / filename),
        "ui": ui,
    }


def _open_endpoint(page, name: str):
    return page.locator('[data-test-id="llm-endpoint"]').filter(has=page.locator("summary", has_text=name))


def _expand(details) -> None:
    if not details.evaluate("element => element.open"):
        details.locator("summary").click()


def _wait_for_catalog(format_locator) -> None:
    trigger = format_locator.locator('[data-test-id="orcarouter-model-trigger"]')
    trigger.click()
    panel = format_locator.locator('[data-test-id="orcarouter-model-panel"]')
    expect(panel).to_be_visible()
    expect(panel.locator('[data-test-id="orcarouter-model-option"]').first).to_be_visible(timeout=60000)
    expect(panel.get_by_text("Verified fallback")).to_be_hidden()
    expect(panel.get_by_text("OrcaRouter rejected", exact=False)).to_be_hidden()


def _create_endpoint(page) -> str:
    section = page.locator('[data-test-id="llm-settings"]')
    details = section.locator("details").filter(has=page.locator("summary", has_text="Add LLM Endpoint"))
    _expand(details)
    form = details.locator('[data-test-id="llm-endpoint-form"]')
    form.locator('select[name="provider"]').select_option("orcarouter")
    expect(form.locator('input[name="base_url"]')).to_have_value("https://api.orcarouter.ai/v1")
    expect(form.locator('[data-test-id="orcarouter-provider-info"]')).to_be_visible()
    form.locator('input[name="name"]').fill("OrcaRouter Cyber Inference")
    form.locator('select[name="enabled"]').select_option("true")
    form.locator('input[name="api_formats[chat_completions][enabled]"]').check()
    form.locator('input[name="api_key"]').fill(API_KEY)
    form.locator('input[name="api_key"]').press("Tab")
    with page.expect_response(
        lambda response: response.request.method == "POST" and response.url.endswith("/llm-endpoints"),
        timeout=60000,
    ) as saved:
        form.get_by_role("button", name="Add Endpoint", exact=True).click()
    if not saved.value.ok:
        raise RuntimeError(f"Endpoint save failed with HTTP {saved.value.status}")
    endpoint = _open_endpoint(page, "OrcaRouter Cyber Inference")
    expect(endpoint).to_have_count(1, timeout=30000)
    return "OrcaRouter Cyber Inference"


def _generate_evidence() -> int:
    if not API_KEY:
        raise RuntimeError("Live OrcaRouter credentials are required for UI evidence")
    if not Path(CHROMIUM).exists():
        raise RuntimeError(f"Chromium is required at {CHROMIUM}")
    core_python = CORE_DIR / ".venv" / "bin" / "python"
    frontend_python = FRONTEND_DIR / ".venv" / "bin" / "python"
    for interpreter in (core_python, frontend_python):
        if not interpreter.exists():
            raise RuntimeError(f"Missing component environment: {interpreter}. Run the setup commands first.")

    EVIDENCE_DIR.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="taranis-orca-evidence-"))
    database = work / "taranis.db"
    log_dir = work / "logs"
    log_dir.mkdir()
    servers = _start(core_python, frontend_python, database, log_dir)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=CHROMIUM, args=["--no-sandbox"])
            context = browser.new_context(viewport={"width": 1440, "height": 1200})
            page = context.new_page()
            page.goto(f"{FRONTEND_URL}/login")
            page.locator("#username").fill("admin")
            page.locator("#password").fill("admin")
            page.get_by_test_id("login-button").click()
            page.wait_for_url(lambda url: "/login" not in url, timeout=30000)
            page.goto(f"{FRONTEND_URL}/admin/settings/")
            expect(page.locator('[data-test-id="llm-settings"]')).to_be_visible(timeout=30000)
            name = _create_endpoint(page)

            endpoint = _open_endpoint(page, name)
            _expand(endpoint)
            chat = endpoint.locator('[data-test-id="llm-format-chat_completions"]')
            chat.scroll_into_view_if_needed()
            _wait_for_catalog(chat)
            options = chat.locator('[data-test-id="orcarouter-model-option"]')
            item_count = options.count()
            panel = chat.locator('[data-test-id="orcarouter-model-panel"]')
            trigger = chat.locator('[data-test-id="orcarouter-model-trigger"]')
            panel.evaluate("element => element.scrollIntoView({block: 'center'})")
            page.wait_for_timeout(4000)
            panel_box = panel.bounding_box()
            if panel_box is None or panel_box["y"] + panel_box["height"] > page.viewport_size["height"]:
                raise RuntimeError("Dropdown panel is not fully visible in the viewport")
            panel_style = panel.evaluate(
                "element => { const style = getComputedStyle(element); const rect = element.getBoundingClientRect(); return {"
                "background: style.backgroundColor, border: style.borderTopWidth, right: rect.right}; }"
            )
            trigger_right = trigger.evaluate("element => element.getBoundingClientRect().right")
            right_delta = abs(panel_style["right"] - trigger_right)
            if right_delta > 2:
                raise RuntimeError(f"Dropdown panel is not aligned with its trigger: {right_delta}px")
            if panel_style["background"].startswith("rgba") and not panel_style["background"].endswith(", 1)"):
                raise RuntimeError(f"Dropdown panel background is not opaque: {panel_style['background']}")
            if panel_style["border"] in {"0px", "0"}:
                raise RuntimeError("Dropdown panel has no visible border")
            if item_count < 3:
                raise RuntimeError(f"Expected at least 3 live models, got {item_count}")
            image_model_count = options.locator("span", has_text="image").count()
            page.screenshot(path=str(EVIDENCE_DIR / "text-model-dropdown.png"), animations="disabled")

            trigger.click()
            expect(panel).to_be_hidden()
            form = endpoint.locator('[data-test-id="llm-endpoint-form"]')
            form.locator('input[name="api_key"]').fill(PLACEHOLDER_KEY)
            expect(form.locator('[data-test-id="orcarouter-api-key-state"]')).to_contain_text("API key is saved")
            api_key_input = form.locator('input[name="api_key"]')
            api_key_visible = api_key_input.is_visible()
            secret_masked = api_key_input.get_attribute("type") == "password" and bool(api_key_input.input_value())
            controls_enabled = (
                form.locator('select[name="provider"]').is_enabled()
                and form.locator('input[name="api_formats[chat_completions][enabled]"]').is_enabled()
                and form.get_by_role("button", name="Save Endpoint", exact=True).is_enabled()
            )
            if not (api_key_visible and secret_masked and controls_enabled):
                raise RuntimeError("API-key controls did not meet the evidence assertions")
            form.locator('[data-test-id="orcarouter-api-key-state"]').evaluate("element => element.scrollIntoView({block: 'center'})")
            page.wait_for_timeout(400)
            page.screenshot(path=str(EVIDENCE_DIR / "auth-methods.png"), animations="disabled")

            browser.close()

        manifest = {
            "automation": {
                "framework": "playwright",
                "passed": True,
                "catalog_source": "https://api.orcarouter.ai/v1/models?capability=chat",
                "catalog_model_count": item_count,
                "image_model_count": image_model_count,
            },
            "artifacts": [
                _artifact(
                    "auth-methods",
                    "auth-methods.png",
                    {"api_key_visible": api_key_visible, "secret_masked": secret_masked, "controls_enabled": controls_enabled},
                ),
                _artifact(
                    "text-model-dropdown",
                    "text-model-dropdown.png",
                    {
                        "dropdown_open": True,
                        "item_count": item_count,
                        "opaque_background": True,
                        "visible_border": True,
                        "trigger_panel_right_delta": round(right_delta, 2),
                    },
                ),
            ],
        }
        (EVIDENCE_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        return item_count
    except Exception:
        print("Core log tail:\n" + _tail(log_dir / "core.log"), file=sys.stderr)
        print("Frontend log tail:\n" + _tail(log_dir / "frontend.log"), file=sys.stderr)
        raise
    finally:
        _stop(servers)
        shutil.rmtree(work, ignore_errors=True)


def test_real_admin_ui_evidence_generation():
    assert _generate_evidence() >= 3

    manifest = json.loads((EVIDENCE_DIR / "manifest.json").read_text())
    automation = manifest["automation"]
    assert automation["framework"] == "playwright"
    assert automation["passed"] is True
    assert automation["catalog_source"] == "https://api.orcarouter.ai/v1/models?capability=chat"
    assert automation["catalog_model_count"] >= 3
    assert 0 <= automation["image_model_count"] <= automation["catalog_model_count"]

    artifacts = {entry["kind"]: entry for entry in manifest["artifacts"]}
    assert set(artifacts) == {"auth-methods", "text-model-dropdown"}
    for entry in artifacts.values():
        image = EVIDENCE_DIR / entry["path"]
        assert image.is_file()
        assert image.stat().st_size >= 10_000
        assert hashlib.sha256(image.read_bytes()).hexdigest() == entry["sha256"]
        width, height = _png_size(image)
        assert width >= 800
        assert height >= 450

    auth = artifacts["auth-methods"]["ui"]
    assert auth == {"api_key_visible": True, "secret_masked": True, "controls_enabled": True}

    dropdown = artifacts["text-model-dropdown"]["ui"]
    assert dropdown["dropdown_open"] is True
    assert dropdown["item_count"] == automation["catalog_model_count"]
    assert dropdown["opaque_background"] is True
    assert dropdown["visible_border"] is True
    assert dropdown["trigger_panel_right_delta"] <= 2
