from pathlib import Path
from urllib.parse import quote

import pytest
from playwright.sync_api import Page, expect


pytestmark = pytest.mark.e2e_ci

MAIN_JS_PATH = Path(__file__).parents[2] / "frontend/static/js/main.js"


def load_main_js(page: Page) -> None:
    html = '<section id="notification-bar"></section>'
    page.goto(f"data:text/html,{quote(html)}")
    page.add_script_tag(path=str(MAIN_JS_PATH))


def test_response_error_notification_does_not_insert_response_markup(page: Page):
    load_main_js(page)

    page.evaluate("""
        () => {
            window.__notificationXss = false;
            const responseText = `
                <section id="notification-bar">
                  <div class="toast toast-center toast-bottom w-1/2 z-50">
                    <div class="alert flex flex-col w-full gap-2 cursor-pointer alert-error" role="alert">
                      <div class="flex items-center gap-2">
                        <span id="notification-message">
                          <img src="invalid" onerror="window.__notificationXss = true">Broken response
                        </span>
                      </div>
                      <div class="w-full h-2 bg-black/20 rounded overflow-hidden">
                        <div class="h-full bg-black animate-shrink-30"></div>
                      </div>
                    </div>
                  </div>
                </section>
            `;
            const detail = { xhr: { responseText } };
            document.body.dispatchEvent(new CustomEvent("htmx:responseError", { bubbles: true, detail }));
        }
    """)

    notification = page.locator("#notification-bar [role='alert']")
    expect(notification).to_contain_text("Broken response")
    assert "alert-error" in notification.evaluate("element => Array.from(element.classList)")
    assert page.locator("#notification-bar img").count() == 0
    assert page.evaluate("() => window.__notificationXss") is False
