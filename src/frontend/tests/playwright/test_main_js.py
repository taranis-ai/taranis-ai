from pathlib import Path
from urllib.parse import quote

import pytest
from playwright.sync_api import Page, expect


pytestmark = pytest.mark.e2e_ci

MAIN_JS_PATH = Path(__file__).parents[2] / "frontend/static/js/main.js"
VENDOR_JS_PATH = Path(__file__).parents[2] / "frontend/static/vendor/vendor.bundle.js"


def load_main_js(page: Page, html: str = '<section id="notification-bar"></section>') -> None:
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


def test_assess_shortcut_guard_ignores_inputs_and_dialogs(page: Page):
    load_main_js(
        page,
        """
        <input id="name">
        <dialog id="story-dialog" open>
          <button id="dialog-button">Close</button>
        </dialog>
        """,
    )

    assert page.evaluate("() => canUseAssessShortcut({ target: document.body })") is False
    assert page.evaluate("() => canUseAssessShortcut({ target: document.querySelector('#name') })") is False
    assert page.evaluate("() => canUseAssessShortcut({ target: document.querySelector('#dialog-button') })") is False

    page.evaluate("() => document.querySelector('#story-dialog').removeAttribute('open')")

    assert page.evaluate("() => canUseAssessShortcut({ target: document.body })") is True


def test_assess_htmx_shortcut_filter_ignores_dialog_typing(page: Page):
    requests = []

    page.route(
        "https://example.test/",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="""
            <button id="bookmark-trigger"
                    hx-get="/bookmark-dialog"
                    hx-trigger="keyup[shiftKey && key == 'B' && canUseAssessShortcut(event)] from:body"
                    hx-target="#result">
              Bookmark
            </button>
            <dialog id="story-bookmark-dialog" open>
              <input id="bookmark-name">
            </dialog>
            <div id="result"></div>
            """,
        ),
    )
    page.route(
        "https://example.test/bookmark-dialog",
        lambda route: (requests.append(route.request.url), route.fulfill(status=200, body="opened")),
    )
    page.goto("https://example.test/")
    page.add_script_tag(path=str(VENDOR_JS_PATH))
    page.add_script_tag(path=str(MAIN_JS_PATH))
    page.evaluate("() => htmx.process(document.body)")

    page.locator("#bookmark-name").focus()
    page.keyboard.press("Shift+B")
    page.wait_for_timeout(100)

    assert requests == []
    expect(page.locator("#result")).to_have_text("")

    page.evaluate("() => document.querySelector('#story-bookmark-dialog').removeAttribute('open')")
    page.locator("body").focus()
    page.keyboard.press("Shift+B")

    expect(page.locator("#result")).to_have_text("opened")
    assert requests == ["https://example.test/bookmark-dialog"]
