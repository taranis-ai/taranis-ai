from pathlib import Path
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


def test_with_htmx_wait_waits_for_swapped_link(htmx_page: Page):
    card = """
        <article id="card">
          <button hx-get="/card" hx-target="#card" hx-swap="outerHTML settle:500ms transition:false">Toggle</button>
          <a id="share" href="/sharing" hx-get="/sharing" hx-target="body" hx-swap="beforeend">Share</a>
        </article>
    """.strip()
    for path in ("", "card"):
        htmx_page.route(f"http://htmx.test/{path}", lambda route: route.fulfill(content_type="text/html", body=card))
    htmx_page.route(
        "http://htmx.test/sharing",
        lambda route: route.fulfill(
            content_type="text/html",
            body="<dialog open>Sharing</dialog>" if route.request.headers.get("hx-request") else "<main>Sharing page</main>",
        ),
    )
    htmx_page.goto("http://htmx.test/")
    htmx_page.add_script_tag(path=str(Path(__file__).parents[2] / "frontend/static/vendor/vendor.bundle.js"))
    htmx_page.evaluate("htmx.config.transitions = false")
    wait_for_htmx_settled(htmx_page)

    htmx_page.get_by_role("button", name="Toggle").click()
    htmx_page.wait_for_function("document.querySelector('#card.htmx-settling') !== null", timeout=1000)
    with_htmx_wait(htmx_page, htmx_page.get_by_role("link", name="Share").click)

    expect(htmx_page.get_by_role("dialog")).to_be_visible()
    expect(htmx_page).to_have_url("http://htmx.test/")


def test_with_htmx_wait_reports_htmx_errors(htmx_page: Page):
    load_html(htmx_page, "<main>Error test</main>")

    with pytest.raises(AssertionError, match=r"HTMX response error .* POST /bad returned 500 Server Error"):
        with_htmx_wait(
            htmx_page,
            lambda: htmx_page.evaluate("""
                () => {
                    const raw = { status: 500, statusText: "Server Error", url: "/bad" };
                    const ctx = {
                        request: { method: "POST", action: "/bad" },
                        response: { status: 500, raw },
                    };
                    const detail = { ctx };
                    document.dispatchEvent(new CustomEvent("htmx:before:request", { bubbles: true, detail }));
                    document.dispatchEvent(new CustomEvent("htmx:response:error", { bubbles: true, detail }));
                    document.dispatchEvent(new CustomEvent("htmx:finally:request", { bubbles: true, detail }));
                }
            """),
            timeout=1000,
        )
