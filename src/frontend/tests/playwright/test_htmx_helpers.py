from urllib.parse import quote

import pytest
from htmx_helpers import install_htmx_support, wait_for_htmx_settled, with_htmx_wait
from playwright.sync_api import Browser, Page, expect


pytestmark = pytest.mark.e2e_ci


@pytest.fixture
def htmx_page(browser: Browser):
    context = browser.new_context()
    install_htmx_support(context)
    page = context.new_page()
    try:
        yield page
    finally:
        page.close()
        context.close()


def load_html(page: Page, html: str) -> None:
    page.goto(f"data:text/html,{quote(html)}")


def test_wait_for_htmx_settled_returns_without_htmx_activity(htmx_page: Page):
    load_html(htmx_page, "<main>No HTMX activity</main>")

    wait_for_htmx_settled(htmx_page, timeout=1000)

    assert htmx_page.evaluate("""() => window.__taranisHtmxTestState.pendingRequests""") == 0


def test_with_htmx_wait_waits_for_after_settle(htmx_page: Page):
    load_html(htmx_page, '<button id="load">Load</button><div id="target"></div>')

    with_htmx_wait(
        htmx_page,
        lambda: htmx_page.evaluate("""
            () => {
                const xhr = { status: 200, statusText: "OK", responseURL: "/fragment" };
                const detail = { xhr, requestConfig: { verb: "GET", path: "/fragment" } };
                document.dispatchEvent(new CustomEvent("htmx:beforeRequest", { bubbles: true, detail }));
                setTimeout(() => {
                    document.querySelector("#target").textContent = "loaded";
                    document.dispatchEvent(new CustomEvent("htmx:afterRequest", { bubbles: true, detail }));
                    document.dispatchEvent(new CustomEvent("htmx:afterSwap", { bubbles: true, detail }));
                    setTimeout(() => {
                        document.dispatchEvent(new CustomEvent("htmx:afterSettle", { bubbles: true, detail }));
                    }, 20);
                }, 20);
            }
        """),
        timeout=1000,
    )

    expect(htmx_page.locator("#target")).to_contain_text("loaded")
    state = htmx_page.evaluate("""() => window.__taranisHtmxTestState""")
    assert state["lastAfterSettle"] >= state["lastAfterSwap"]


def test_with_htmx_wait_reports_htmx_errors(htmx_page: Page):
    load_html(htmx_page, "<main>Error test</main>")

    with pytest.raises(AssertionError, match=r"HTMX response error .* POST /bad returned 500 Server Error"):
        with_htmx_wait(
            htmx_page,
            lambda: htmx_page.evaluate("""
                () => {
                    const xhr = { status: 500, statusText: "Server Error", responseURL: "/bad" };
                    const detail = { xhr, requestConfig: { verb: "POST", path: "/bad" } };
                    document.dispatchEvent(new CustomEvent("htmx:beforeRequest", { bubbles: true, detail }));
                    document.dispatchEvent(new CustomEvent("htmx:responseError", { bubbles: true, detail }));
                }
            """),
            timeout=1000,
        )
