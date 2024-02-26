#!/usr/bin/env python3

from playwright.sync_api import Playwright
import time
import os

taranis_url = os.getenv("TARANIS_URL", "http://localhost:8081")


def click_with_highlight(locator, duration=2):
    # Add a style tag to the head of the document with the highlight style
    style_content = """
    .highlight-element { background-color: yellow; outline: 4px solid red; }
    """

    locator.page.add_style_tag(content=style_content)

    # Add the 'highlight-element' class to the element we want to highlight
    locator.evaluate("element => element.classList.add('highlight-element')")
    time.sleep(duration)
    locator.click()


def scroll_to_the_bottom(page):
    last_height = page.evaluate("document.documentElement.scrollHeight")
    current = 0
    while current < last_height:
        # Scroll down by a certain amount
        scroll_pixels = 300
        page.evaluate(f"window.scrollBy(0, {scroll_pixels})")
        time.sleep(0.5)
        current += scroll_pixels


def test_run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False, slow_mo=1000)
    context = browser.new_context(
        record_video_dir="videos/",
        viewport={"width": 1920, "height": 1080},
        record_video_size={"width": 1810, "height": 1000},
    )

    page = context.new_page()
    page.goto(f"{taranis_url}/login")
    click_with_highlight(page.get_by_placeholder("Username"))

    page.get_by_placeholder("Username").fill("admin")
    click_with_highlight(page.get_by_placeholder("Password"))
    page.get_by_placeholder("Password").fill("admin")

    click_with_highlight(page.locator("role=button"))
    click_with_highlight(page.locator('role=link[name="Assess"]').first)
    click_with_highlight(page.get_by_role("button", name="relevance"))
    click_with_highlight(page.get_by_role("button", name="Expand [12]"))
    click_with_highlight(page.get_by_role("button", name="Collapse [12]"))
    click_with_highlight(page.locator(".v-col-sm-12 > a").first)
    scroll_to_the_bottom(page)
    click_with_highlight(page.get_by_role("link", name="Dashboard"))
    click_with_highlight(page.get_by_role("link", name="Lazarus Group"))
    click_with_highlight(page.get_by_role("button", name="Expand [6]"))
    click_with_highlight(page.get_by_text("Spain", exact=True))
    click_with_highlight(page.get_by_role("link", name="open"))
    click_with_highlight(page.get_by_role("button", name="add to Report"))
    click_with_highlight(page.get_by_role("button", name="Select Report Open"))
    click_with_highlight(page.get_by_text("Weekly report"))
    click_with_highlight(page.get_by_role("button", name="share"))
    click_with_highlight(page.get_by_role("link", name="Analyze"))
    click_with_highlight(page.get_by_role("cell", name="Weekly report"))
    click_with_highlight(page.get_by_role("button", name="Vulnerability", exact=True))
    click_with_highlight(page.get_by_role("button", name="Open", exact=True))
    click_with_highlight(page.get_by_text("Unauthorized access to the system"))
    click_with_highlight(page.get_by_label("Description"))
    page.get_by_label("Description").fill("Espionage in North Korea")
    # page.get_by_label("Completed").check()
    click_with_highlight(page.get_by_role("button", name="Save"))
    click_with_highlight(page.get_by_role("link", name="Publish"))
    click_with_highlight(page.get_by_role("cell", name="Events of the 25th week"))
    click_with_highlight(page.get_by_role("button", name="Render Product"))
    page.reload()

    context.close()
    browser.close()


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        test_run(p)
