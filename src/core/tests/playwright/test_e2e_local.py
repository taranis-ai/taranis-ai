#!/usr/bin/env python3

from playwright.sync_api import Playwright
import time
import os
import pytest

taranis_url = os.getenv("TARANIS_URL", "http://localhost:8081")


def highlight_element(locator, duration=2):
    # Define the highlight style
    style_content = """
    .highlight-element { background-color: yellow; outline: 4px solid red; }
    """

    # Add a style tag to the head of the document with the highlight style
    style_tag = locator.page.add_style_tag(content=style_content)

    # Add the 'highlight-element' class to the element to be highlighted
    locator.evaluate("element => element.classList.add('highlight-element')")

    # Sleep for the duration of the highlight
    time.sleep(duration)

    # Remove the 'highlight-element' class from the element
    locator.evaluate("element => element.classList.remove('highlight-element')")

    # Optionally, remove the style tag if it's not needed elsewhere
    locator.page.evaluate(f"style => style.remove()", style_tag)

    return locator


def scroll_to_the_bottom(page):
    last_height = page.evaluate("document.documentElement.scrollHeight")
    current = 0
    while current < last_height:
        # Scroll down by a certain amount
        scroll_pixels = 300
        page.evaluate(f"window.scrollBy(0, {scroll_pixels})")
        time.sleep(0.5)
        current += scroll_pixels


@pytest.mark.e2e
def test_e2e(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False, slow_mo=1000)
    context = browser.new_context(
        # record_video_dir="videos/",
        viewport={"width": 1920, "height": 1080},
        record_video_size={"width": 1810, "height": 1000},
    )

    page = context.new_page()
    page.goto(f"{taranis_url}/login")
    highlight_element(page.get_by_placeholder("Username"))

    page.get_by_placeholder("Username").fill("admin")
    highlight_element(page.get_by_placeholder("Password"))
    page.get_by_placeholder("Password").fill("admin")
    highlight_element(page.locator("role=button")).click()

    highlight_element(page.locator('role=link[name="Assess"]').first).click()
    highlight_element(page.get_by_role("button", name="relevance")).click()
    highlight_element(page.get_by_role("button", name="Expand [12]")).click()
    highlight_element(page.get_by_role("button", name="Collapse [12]")).click()
    highlight_element(page.locator(".v-col-sm-12 > a").first).click()
    scroll_to_the_bottom(page)
    highlight_element(page.get_by_role("link", name="Dashboard")).click()
    highlight_element(page.get_by_role("link", name="Lazarus Group")).click()
    highlight_element(page.get_by_role("button", name="Expand [6]")).click()
    highlight_element(page.get_by_text("Spain", exact=True)).click()
    highlight_element(page.get_by_role("link", name="open")).click()
    highlight_element(page.get_by_role("button", name="add to Report")).click()
    highlight_element(page.get_by_role("button", name="Select Report Open")).click()
    highlight_element(page.get_by_text("Weekly report")).click()
    highlight_element(page.get_by_role("button", name="share")).click()
    highlight_element(page.get_by_role("link", name="Analyze")).click()
    highlight_element(page.get_by_role("cell", name="Weekly report")).click()
    highlight_element(page.get_by_role("button", name="Vulnerability", exact=True)).click()
    highlight_element(page.get_by_role("button", name="Open", exact=True)).click()
    highlight_element(page.get_by_text("Unauthorized access to the system")).click()
    highlight_element(page.get_by_label("Description")).click()
    page.get_by_label("Description").fill("Espionage in North Korea").click()
    # page.get_by_label("Completed").check()
    highlight_element(page.get_by_role("button", name="Save")).click()
    highlight_element(page.get_by_role("link", name="Publish")).click()
    highlight_element(page.get_by_role("cell", name="Events of the 25th week")).click()
    highlight_element(page.get_by_role("button", name="Render Product")).click()
    page.reload()

    context.close()
    browser.close()
