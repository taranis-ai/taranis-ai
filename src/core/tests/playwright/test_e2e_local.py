#!/usr/bin/env python3
import re

from playwright.sync_api import Playwright, expect
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
        # record_video_size={"width": 1810, "height": 1000},
    )
    page = context.new_page()
    page.goto("http://localhost:8081/login")
    page.get_by_placeholder("Username").click()
    page.get_by_placeholder("Username").fill("admin")
    page.get_by_placeholder("Username").press("Tab")
    page.get_by_placeholder("Password").fill("admin")
    page.get_by_placeholder("Password").press("Enter")
    page.get_by_role("link", name="Assess").first.click()

    page.get_by_label("Open").nth(1).click()
    page.get_by_label("Source Group", exact=True).click()
    page.locator(".v-col > .v-input > .v-input__control > .v-field > .v-field__append-inner").first.click()
    page.get_by_label("Open").nth(2).click()
    page.get_by_role("option", name="Test Source").click()
    page.locator(".w-100").click()
    page.locator("body").press("Escape")

    expect(page.get_by_role("main")).to_contain_text(
        "Bundesinnenministerin Nancy Faeser wird Claudia Plattner zur neuen BSI-Präsidentin berufen"
    )
    expect(page.get_by_role("main")).to_contain_text(
        "Claudia Plattner wird ab 1. Juli 2023 das Bundesamt für Sicherheitin der Informationstechnik (BSI) leiten."
    )
    page.locator(".ml-auto > button").first.click()
    expect(page.get_by_role("main")).to_contain_text("TEST CONTENT XXXX")
    expect(page.get_by_role("main")).to_contain_text("Mobile World Congress 2023")
    expect(page.get_by_role("main")).to_contain_text("TEST CONTENT YYYY")
    page.locator("div:nth-child(3) > div:nth-child(2) > div > div:nth-child(2) > .ml-auto > button").first.click()
    expect(page.get_by_role("main")).to_contain_text("TEST CONTENT YYYY")
    page.locator(".v-col-lg-8").first.click()
    page.get_by_text("Mobile World Congress 2023TEST CONTENT YYYY").click()
    page.get_by_role("button", name="merge").click()
    expect(page.get_by_role("main")).to_contain_text("(2)")
    page.get_by_role("link", name="Analyze").click()
    page.get_by_role("button", name="New Report").click()
    page.get_by_role("combobox").locator("div").filter(has_text="Report Item TypeReport Item").locator("div").click()
    expect(page.get_by_role("listbox")).to_contain_text("CERT Report")
    expect(page.get_by_role("listbox")).to_contain_text("Disinformation")
    expect(page.get_by_role("listbox")).to_contain_text("OSINT Report")
    expect(page.get_by_role("listbox")).to_contain_text("Vulnerability Report")
    page.get_by_label("Title").click()
    page.get_by_label("Title").fill("Test Title")
    page.get_by_role("combobox").locator("i").click()
    page.get_by_role("option", name="Disinformation").click()
    page.get_by_role("button", name="Save").click()
    page.get_by_role("link", name="Assess").click()
    page.get_by_role("main").get_by_role("button").nth(1).click()
    page.get_by_role("dialog").get_by_label("Open").click()
    page.get_by_role("option", name="Test Title").click()
    page.get_by_role("button", name="share").click()
    page.get_by_role("link", name="Analyze").click()
    expect(page.locator("tbody")).to_contain_text("Disinformation")
    expect(page.locator("tbody")).to_contain_text("Test Title")
    expect(page.locator("tbody")).to_contain_text("1")
    page.get_by_role("link", name="Publish").click()
    page.get_by_role("button", name="New Product").click()
    page.get_by_role("combobox").locator("div").filter(has_text="Product TypeProduct Type").locator("div").click()
    page.get_by_role("option", name="Default TEXT Presenter").click()
    page.get_by_label("Title").click()
    page.get_by_label("Title").fill("Test Product")
    page.get_by_label("Description").click()
    page.get_by_label("Description").fill("Test Description")
    page.get_by_role("button", name="Create").click()
    expect(page.get_by_role("main").locator("header").get_by_role("button", name="Render Product")).to_be_visible()
    expect(page.locator("div").filter(has_text=re.compile(r"^Render Product$")).get_by_role("button")).to_be_visible()
    expect(page.locator("div").filter(has_text=re.compile(r"^Render Product first, to enable publishing$")).nth(1)).to_be_visible()
    expect(page.get_by_role("button", name="Save")).to_be_visible()
    # page.get_by_role("main").locator("header").get_by_role("button", name="Render Product").click()
    # page.reload()
    # page.locator("div").filter(has_text=re.compile(r"^Render Product$")).get_by_role("button").click()
    page.get_by_role("link", name="Analyze").click()
    page.get_by_role("cell", name="false").click()
    page.get_by_text("Edit report item - Test Title").click()
    page.get_by_role("link", name="Analyze").click()
    page.get_by_role("cell", name="Test Title").click()

    # Filling the extended discription of the report item can be tricky. If get_by_role() is used with click()
    # (in case of a "textbox") then it is proceeded with get_by_role with fill() then the test fails because
    # the locator changes after the first click.
    # Solution: use the new locator for fill() or skip the first click.

    # page.get_by_role("textbox", name="title").click()
    page.get_by_role("textbox", name="title").fill("Test Title of Report")
    # page.get_by_label("Quote").fill("Test")
    page.get_by_label("Quote").fill("Test Quote")
    # page.get_by_label("Date started").click()
    page.get_by_label("Ransomware").click()
    page.get_by_label("Ransomware").fill("Test Ransomware Name")
    page.get_by_label("Actor").click()
    page.get_by_label("Actor").fill("Test APT")
    page.locator("div:nth-child(3) > div > .v-input > .v-input__control > .v-field > .v-field__field > .v-field__input").click()
    page.get_by_role("option", name="Energy", exact=True).click()
    # page.get_by_label("Comment").click()
    page.get_by_label("Comment").fill("Test Sector Comment")
    page.get_by_role("button", name="Save").click()
    expect(page.get_by_text("Side-by-side")).to_be_visible()
    expect(page.get_by_text("Completed")).to_be_visible()
    expect(page.get_by_role("button", name="Save")).to_be_visible()
    expect(page.get_by_role("button", name="remove all stories")).to_be_visible()
    expect(page.get_by_label("Side-by-side")).to_be_visible()
    expect(page.locator(".v-switch__track").first).to_be_visible()
    expect(page.get_by_label("Completed")).to_be_visible()
    expect(page.locator("div:nth-child(4) > .v-input__control > .v-selection-control > .v-selection-control__wrapper")).to_be_visible()
    page.get_by_label("Side-by-side").check()
    page.get_by_label("Completed").check()
    page.get_by_role("button", name="Save").click()
    # page.get_by_label("Date started").click()
    # page.get_by_label("Date started").click()
    page.get_by_role("link", name="Analyze").click()
    expect(page.locator("tbody")).to_contain_text("true")
    page.get_by_role("link", name="Publish").click()
    page.get_by_role("cell", name="Test Product").click()
    expect(page.locator("tbody")).to_contain_text("complete")

    # old
    # browser = playwright.chromium.launch(headless=False, slow_mo=1000)
    # context = browser.new_context(
    #     # record_video_dir="videos/",
    #     viewport={"width": 1920, "height": 1080},
    #     record_video_size={"width": 1810, "height": 1000},
    # )
    #
    # page = context.new_page()
    # page.goto(f"{taranis_url}/login")
    # highlight_element(page.get_by_placeholder("Username"))
    #
    # page.get_by_placeholder("Username").fill("admin")
    # highlight_element(page.get_by_placeholder("Password"))
    # page.get_by_placeholder("Password").fill("admin")
    # highlight_element(page.locator("role=button")).click()
    #
    # highlight_element(page.locator('role=link[name="Assess"]').first).click()
    # highlight_element(page.get_by_role("button", name="relevance")).click()
    # highlight_element(page.get_by_role("button", name="Expand [12]")).click()
    # highlight_element(page.get_by_role("button", name="Collapse [12]")).click()
    # highlight_element(page.locator(".v-col-sm-12 > a").first).click()
    # scroll_to_the_bottom(page)
    # highlight_element(page.get_by_role("link", name="Dashboard")).click()
    # highlight_element(page.get_by_role("link", name="Lazarus Group")).click()
    # highlight_element(page.get_by_role("button", name="Expand [6]")).click()
    # highlight_element(page.get_by_text("Spain", exact=True)).click()
    # highlight_element(page.get_by_role("link", name="open")).click()
    # highlight_element(page.get_by_role("button", name="add to Report")).click()
    # highlight_element(page.get_by_role("button", name="Select Report Open")).click()
    # highlight_element(page.get_by_text("Weekly report")).click()
    # highlight_element(page.get_by_role("button", name="share")).click()
    # highlight_element(page.get_by_role("link", name="Analyze")).click()
    # highlight_element(page.get_by_role("cell", name="Weekly report")).click()
    # highlight_element(page.get_by_role("button", name="Vulnerability", exact=True)).click()
    # highlight_element(page.get_by_role("button", name="Open", exact=True)).click()
    # highlight_element(page.get_by_text("Unauthorized access to the system")).click()
    # highlight_element(page.get_by_label("Description")).click()
    # page.get_by_label("Description").fill("Espionage in North Korea").click()
    # # page.get_by_label("Completed").check()
    # highlight_element(page.get_by_role("button", name="Save")).click()
    # highlight_element(page.get_by_role("link", name="Publish")).click()
    # highlight_element(page.get_by_role("cell", name="Events of the 25th week")).click()
    # highlight_element(page.get_by_role("button", name="Render Product")).click()
    # page.reload()
    #
    context.close()
    browser.close()
