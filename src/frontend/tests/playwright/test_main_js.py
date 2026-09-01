import re
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import pytest
from playwright.sync_api import Page, expect


pytestmark = pytest.mark.e2e_ci

MAIN_JS_PATH = Path(__file__).parents[2] / "frontend/static/js/main.js"
STORY_CONFLICTS_TEMPLATE_PATH = Path(__file__).parents[2] / "frontend/templates/conflicts/story_conflicts.html"
VENDOR_JS_PATH = Path(__file__).parents[2] / "frontend/static/vendor/vendor.bundle.js"


def load_main_js(page: Page, html: str = '<section id="notification-bar"></section>') -> None:
    page.goto(f"data:text/html,{quote(html)}")
    page.add_script_tag(path=str(MAIN_JS_PATH))


def test_vendor_bundle_uses_htmx_4(page: Page):
    page.goto("data:text/html,<main></main>")
    page.add_script_tag(path=str(VENDOR_JS_PATH))

    assert page.evaluate("() => window.htmx.version") == "4.0.0"


def test_story_conflict_editors_mount_after_outer_html_replacement(page: Page):
    script_match = re.search(r"<script>(.*?)</script>", STORY_CONFLICTS_TEMPLATE_PATH.read_text(), re.DOTALL)
    assert script_match

    page.set_content('<div id="story-conflicts-wrapper"></div>')
    page.evaluate("""
        () => {
            window.TemplateEditor = {
                mountUnifiedMerge: () => ({ state: { doc: { toString: () => "resolved" } } }),
            };
        }
    """)
    page.add_script_tag(content=script_match.group(1))
    page.evaluate("""
        () => {
            const previousTarget = document.getElementById("story-conflicts-wrapper");
            const replacement = document.createElement("div");
            replacement.id = "story-conflicts-wrapper";
            replacement.innerHTML = `<div data-merge-editor data-existing='"old"' data-incoming='"new"'></div>`;
            previousTarget.replaceWith(replacement);
            document.body.dispatchEvent(new CustomEvent("htmx:after:swap", {
                detail: { ctx: { target: previousTarget } },
            }));
        }
    """)

    expect(page.locator("[data-merge-editor]")).to_have_attribute("data-merge-editor-initialized", "1")


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
            const detail = { ctx: { text: responseText } };
            document.body.dispatchEvent(new CustomEvent("htmx:response:error", { bubbles: true, detail }));
        }
    """)

    notification = page.locator("#notification-bar [role='alert']")
    expect(notification).to_contain_text("Broken response")
    assert "alert-error" in notification.evaluate("element => Array.from(element.classList)")
    assert page.locator("#notification-bar img").count() == 0
    assert page.evaluate("() => window.__notificationXss") is False


@pytest.mark.parametrize("level", ["error", "warning", "success", "info"])
def test_response_error_notification_preserves_supported_level(page: Page, level: str):
    load_main_js(page)

    page.evaluate(
        """
        (level) => {
            window.taranisNotifications = { add: (entry) => { window.__recordedNotification = entry; } };
            const responseText = `
                <section id="notification-bar">
                  <div class="alert alert-${level}" role="alert">
                    <span id="notification-message">Request message</span>
                  </div>
                </section>
            `;
            const detail = { ctx: { text: responseText } };
            document.body.dispatchEvent(new CustomEvent("htmx:response:error", { bubbles: true, detail }));
        }
        """,
        level,
    )

    notification = page.locator("#notification-bar [role='alert']")
    assert f"alert-{level}" in notification.evaluate("element => Array.from(element.classList)")
    assert page.evaluate("() => window.__recordedNotification.level") == level


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


def test_assess_shift_space_prevents_scroll_and_requires_selection(page: Page):
    requests = []
    page.route(
        "https://example.test/",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="""
            <div x-data="{ selectedItems: [] }"
                 @keydown.window="preventAssessShortcutDefault($event, 'Space')"
                 style="height: 4000px">
              <button id="read-trigger"
                      hx-post="/read"
                      hx-trigger="click"
                      hx-vals='{"action": "read"}'
                      @keyup.window="canUseAssessShortcut($event) && $event.shiftKey && $event.code === 'Space' && selectedItems.length > 0 && $el.click()">
                Read
              </button>
              <button id="select" @click="selectedItems = ['story-1']">Select</button>
            </div>
            """,
        ),
    )
    page.route(
        "https://example.test/read",
        lambda route: (requests.append(route.request), route.fulfill(status=200, body="updated")),
    )
    page.goto("https://example.test/")
    page.add_script_tag(path=str(VENDOR_JS_PATH))
    page.add_script_tag(path=str(MAIN_JS_PATH))
    page.wait_for_function("() => window.Alpine")
    page.evaluate("() => htmx.process(document.body)")
    page.evaluate("() => window.scrollTo(0, 1800)")

    page.keyboard.press("Shift+Space")
    assert requests == []
    assert page.evaluate("() => window.scrollY") == 1800

    page.locator("#select").click()
    with page.expect_response("https://example.test/read"):
        page.keyboard.press("Shift+Space")

    expect(page.locator("#read-trigger")).to_have_text("updated")
    assert requests[0].post_data_json == {"action": "read"}


def test_assess_shift_e_shortcut_uses_selected_story(page: Page):
    html = quote("""
        <div x-data="{
          selectedItems: ['story-1'],
          openStoryEdit() { document.querySelector('#opened').textContent = this.selectedItems[0]; }
        }">
          <button @keyup.window="canUseAssessShortcut($event, 'e') && selectedItems.length === 1 && openStoryEdit()">Edit</button>
          <output id="opened"></output>
        </div>
    """)
    page.goto(f"data:text/html,{html}")
    page.add_script_tag(path=str(VENDOR_JS_PATH))
    page.add_script_tag(path=str(MAIN_JS_PATH))
    page.wait_for_function("() => window.Alpine")

    page.keyboard.press("e")
    page.keyboard.press("Shift+R")

    expect(page.locator("#opened")).to_have_text("")

    page.keyboard.press("Shift+E")

    expect(page.locator("#opened")).to_have_text("story-1")


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


def test_htmx_uses_configured_csrf_cookie(page: Page):
    csrf_headers = []
    page.context.add_cookies([{"name": "csrf_access_token_q", "value": "csrf-value", "url": "https://example.test"}])
    page.route(
        "https://example.test/",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="""
            <body data-csrf-cookie-name="csrf_access_token_q">
              <button id="submit" hx-post="/submit" hx-target="#result">Submit</button>
              <div id="result"></div>
            </body>
            """,
        ),
    )
    page.route(
        "https://example.test/submit",
        lambda route: (
            csrf_headers.append(route.request.headers.get("x-csrf-token")),
            route.fulfill(status=200, body="saved"),
        ),
    )
    page.goto("https://example.test/")
    page.add_script_tag(path=str(VENDOR_JS_PATH))
    page.add_script_tag(path=str(MAIN_JS_PATH))
    page.evaluate("() => htmx.process(document.body)")

    page.locator("#submit").click()

    expect(page.locator("#result")).to_have_text("saved")
    assert csrf_headers == ["csrf-value"]


def test_htmx_confirmation_can_cancel_and_add_force_delete_data(page: Page):
    requests = []
    page.route(
        "https://example.test/",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="""
            <body data-confirm-delete="Delete" data-confirm-cancel="Cancel">
              <button id="delete"
                      hx-delete="/resource"
                      hx-vals='{"ids":["one","two"]}'
                      hx-confirm="Delete this resource?"
                      data-force-delete>Delete</button>
            </body>
            """,
        ),
    )
    page.route(
        "https://example.test/resource*",
        lambda route: (requests.append(route.request.url), route.fulfill(status=200, body="deleted")),
    )
    page.goto("https://example.test/")
    page.add_script_tag(path=str(VENDOR_JS_PATH))
    page.add_script_tag(path=str(MAIN_JS_PATH))
    page.evaluate("() => htmx.process(document.body)")

    page.evaluate("() => { Swal.fire = () => Promise.resolve({ isConfirmed: false }); }")
    page.locator("#delete").click()
    page.wait_for_timeout(100)

    assert requests == []

    page.evaluate("() => { Swal.fire = () => Promise.resolve({ isConfirmed: true, value: true }); }")
    page.locator("#delete").click()

    expect(page.locator("body")).to_contain_text("deleted")
    assert requests == ["https://example.test/resource?ids=one&ids=two&force=true"]


def test_htmx_native_status_rules_preserve_error_swap_behavior(page: Page):
    def response_handler(status: int, body: str):
        def fulfill(route):
            route.fulfill(status=status, body=body)

        return fulfill

    for path, status, body in (
        ("validation", 400, "validation error"),
        ("targeted-client", 422, "targeted client error"),
        ("targeted-server", 503, "targeted server error"),
        ("generic-server", 500, "generic server error"),
    ):
        page.route(
            f"https://example.test/{path}",
            response_handler(status, body),
        )

    page.route(
        "https://example.test/",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="""
            <body hx-status:400:inherited="{}"
                  hx-status:4xx:inherited="swap:none"
                  hx-status:5xx:inherited="swap:none">
              <button id="validation" hx-get="/validation" hx-target="#content">Validation</button>
              <button id="targeted-client"
                      hx-get="/targeted-client"
                      hx-status:400="target:#errors"
                      hx-status:4xx="target:#errors"
                      hx-status:5xx="target:#errors">Client error</button>
              <button id="targeted-server"
                      hx-get="/targeted-server"
                      hx-status:400="target:#errors"
                      hx-status:4xx="target:#errors"
                      hx-status:5xx="target:#errors">Server error</button>
              <button id="generic-server" hx-get="/generic-server" hx-target="#content">Generic error</button>
              <div id="content">original content</div>
              <div id="errors">no error</div>
              <section id="notification-bar"></section>
            </body>
            """,
        ),
    )
    page.goto("https://example.test/")
    page.add_script_tag(path=str(VENDOR_JS_PATH))
    page.add_script_tag(path=str(MAIN_JS_PATH))
    page.evaluate("() => htmx.process(document.body)")

    page.locator("#validation").click()
    expect(page.locator("#content")).to_have_text("validation error")

    page.locator("#targeted-client").click()
    expect(page.locator("#errors")).to_have_text("targeted client error")

    page.locator("#targeted-server").click()
    expect(page.locator("#errors")).to_have_text("targeted server error")

    page.locator("#generic-server").click()
    page.wait_for_timeout(100)
    expect(page.locator("#content")).to_have_text("validation error")


def test_htmx_filter_control_includes_its_form(page: Page):
    requests = []
    filter_markup = """
        <div id="results">
          <form hx-target:inherited="#results"
                hx-select:inherited="#results"
                hx-swap:inherited="outerHTML"
                hx-push-url:inherited="true"
                hx-on::before:request="restoreSearchAfterSwap(ctx)">
            <input name="search"
                   value=""
                   data-search-from-request
                   data-focus-after-swap
                   hx-get="/filter"
                   hx-include="closest form"
                   hx-trigger="input changed delay:10ms">
            <select id="status"
                    name="status"
                    hx-get="/filter"
                    hx-include="closest form"
                    hx-trigger="change">
              <option value="">All</option>
              <option value="open">Open</option>
            </select>
          </form>
        </div>
    """
    page.route(
        "https://example.test/",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body=filter_markup,
        ),
    )
    page.route(
        "https://example.test/filter*",
        lambda route: (
            requests.append(route.request.url),
            route.fulfill(
                status=200,
                body=filter_markup.replace(
                    'value=""',
                    f'value="{parse_qs(urlparse(route.request.url).query).get("search", [""])[0]}"',
                    1,
                ),
            ),
        ),
    )
    page.goto("https://example.test/")
    page.add_script_tag(path=str(VENDOR_JS_PATH))
    page.add_script_tag(path=str(MAIN_JS_PATH))
    page.evaluate("() => htmx.process(document.body)")

    page.locator("[name='search']").fill("incident")
    expect(page).to_have_url(re.compile(r"search=incident"))
    expect(page.locator("#results [name='search']")).to_have_value("incident")
    page.locator("#status").select_option("open")

    expect(page.locator("#results [name='search']")).to_have_value("incident")
    assert requests == [
        "https://example.test/filter?search=incident&status=",
        "https://example.test/filter?status=open&search=incident",
    ]
