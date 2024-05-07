#!/usr/bin/env python3
import re

from playwright.sync_api import sync_playwright, expect
import time
import os
import pytest

app = None

taranis_url = os.getenv("TARANIS_URL", "http://localhost:8081")
print(taranis_url)


# os.environ["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg2://taranis:supersecret@localhost/taranis"
# os.environ["API_KEY"] = "supersecret"
# os.environ["SECRET_KEY"] = "supersecret"
# os.unsetenv("PRE_SEED_PASSWORD_USER")


def highlight_element(locator, duration):
    style_content = """
    .highlight-element { background-color: yellow; outline: 4px solid red; }
    """

    style_tag = locator.page.add_style_tag(content=style_content)
    locator.evaluate("element => element.classList.add('highlight-element')")
    time.sleep(duration)
    locator.evaluate("element => element.classList.remove('highlight-element')")
    locator.page.evaluate("style => style.remove()", style_tag)
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


def run_e2e(
    playwright,
    headless=True,
    video_dir=None,
    viewport=None,
    record_video_size=None,
    wait=1,
) -> None:
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context(
        record_video_dir=video_dir,
        viewport=viewport,
        record_video_size=record_video_size,
    )
    page = context.new_page()
    page.goto(taranis_url)
    (page.get_by_placeholder("Username"))

    page.get_by_placeholder("Username").fill("admin")
    highlight_element(page.get_by_placeholder("Password"), wait)
    page.get_by_placeholder("Password").fill("admin")
    highlight_element(page.locator("role=button"), wait).click()
    highlight_element(page.get_by_role("link", name="Assess").first, wait).click()

    highlight_element(page.get_by_label("Source", exact=True), wait).click()

    highlight_element(page.get_by_role("option", name="Test Source"), wait).click()
    page.locator("body").press("Escape")

    expect(page.get_by_role("main")).to_contain_text(
        "Bundesinnenministerin Nancy Faeser wird Claudia Plattner zur neuen BSI-Präsidentin berufen"
    )
    expect(page.get_by_role("main")).to_contain_text(
        "Claudia Plattner wird ab 1. Juli 2023 das Bundesamt für Sicherheitin der Informationstechnik (BSI) leiten."
    )
    highlight_element(page.locator(".ml-auto > button").first, wait).click()
    expect(page.get_by_role("main")).to_contain_text("TEST CONTENT XXXX")
    expect(page.get_by_role("main")).to_contain_text("Mobile World Congress 2023")
    expect(page.get_by_role("main")).to_contain_text("TEST CONTENT YYYY")
    highlight_element(page.locator("div:nth-child(3) > div:nth-child(2) > div > div:nth-child(2) > .ml-auto > button").first, wait).click()
    expect(page.get_by_role("main")).to_contain_text("TEST CONTENT YYYY")
    highlight_element(page.get_by_role("heading", name="Bundesinnenministerin Nancy"), wait).click()
    highlight_element(page.get_by_text("Mobile World Congress 2023TEST CONTENT YYYY"), wait).click()
    highlight_element(page.get_by_role("button", name="merge"), wait).click()
    expect(page.get_by_role("main")).to_contain_text("(2)")
    highlight_element(page.locator(".ml-auto > button").first, wait).click()
    highlight_element(page.get_by_role("link", name="Analyze"), wait).click()
    highlight_element(page.get_by_role("button", name="New Report"), wait).click()
    highlight_element(page.get_by_role("combobox").locator("i"), wait).click()
    expect(page.get_by_role("listbox")).to_contain_text("CERT Report")
    expect(page.get_by_role("listbox")).to_contain_text("Disinformation")
    expect(page.get_by_role("listbox")).to_contain_text("OSINT Report")
    expect(page.get_by_role("listbox")).to_contain_text("Vulnerability Report")
    highlight_element(page.get_by_role("option", name="Disinformation"), wait).click()
    highlight_element(page.get_by_label("Title"), wait).click()
    highlight_element(page.get_by_label("Title"), wait).fill("Test Title")
    highlight_element(page.get_by_role("button", name="Save"), wait).click()
    highlight_element(page.get_by_role("link", name="Assess"), wait).click()
    highlight_element(page.get_by_role("main").get_by_role("button").nth(1), wait).click()
    highlight_element(page.get_by_role("dialog").get_by_label("Open"), wait).click()
    highlight_element(page.get_by_role("option", name="Test Title"), wait).click()
    highlight_element(page.get_by_role("button", name="share"), wait).click()
    highlight_element(page.get_by_role("link", name="Analyze"), wait).click()
    expect(page.locator("tbody")).to_contain_text("Disinformation")
    expect(page.locator("tbody")).to_contain_text("Test Title")
    expect(page.locator("tbody")).to_contain_text("1")
    highlight_element(page.get_by_role("link", name="Publish"), wait).click()
    highlight_element(page.get_by_role("button", name="New Product"), wait).click()
    highlight_element(page.get_by_role("combobox").locator("div").filter(has_text="Product TypeProduct Type").locator("div"), wait).click()
    highlight_element(page.get_by_role("option", name="Default TEXT Presenter"), wait).click()
    highlight_element(page.get_by_label("Title"), wait).click()
    highlight_element(page.get_by_label("Title"), wait).fill("Test Product")
    highlight_element(page.get_by_label("Description"), wait).click()
    highlight_element(page.get_by_label("Description"), wait).fill("Test Description")
    highlight_element(page.get_by_role("button", name="Create"), wait).click()
    expect(page.get_by_role("main").locator("header").get_by_role("button", name="Render Product")).to_be_visible()
    expect(page.locator("div").filter(has_text=re.compile(r"^Render Product$")).get_by_role("button")).to_be_visible()
    expect(page.locator("div").filter(has_text=re.compile(r"^Render Product first, to enable publishing$")).nth(1)).to_be_visible()
    expect(page.get_by_role("button", name="Save")).to_be_visible()
    highlight_element(page.get_by_role("link", name="Analyze"), wait).click()
    highlight_element(page.get_by_role("cell", name="false"), wait).click()
    highlight_element(page.get_by_role("textbox", name="title"), wait).fill("Test Title of Report")
    highlight_element(page.get_by_label("Quote"), wait).fill("Test Quote")
    highlight_element(page.get_by_label("Ransomware"), wait).click()
    highlight_element(page.get_by_label("Ransomware"), wait).fill("Test Ransomware Name")
    highlight_element(page.get_by_label("Actor"), wait).click()
    highlight_element(page.get_by_label("Actor"), wait).fill("Test APT")
    highlight_element(
        page.locator("div:nth-child(3) > div > .v-input > .v-input__control > .v-field > .v-field__field > .v-field__input"), wait
    ).click()
    highlight_element(page.get_by_role("option", name="Energy", exact=True), wait).click()
    highlight_element(page.get_by_label("Comment"), wait).fill("Test Sector Comment")
    highlight_element(page.get_by_role("button", name="Save"), wait).click()
    expect(page.get_by_text("Side-by-side")).to_be_visible()
    expect(page.get_by_text("Completed")).to_be_visible()
    expect(page.get_by_role("button", name="Save")).to_be_visible()
    expect(page.get_by_role("button", name="remove all stories")).to_be_visible()
    expect(page.get_by_label("Side-by-side")).to_be_visible()
    expect(page.locator(".v-switch__track").first).to_be_visible()
    expect(page.get_by_label("Completed")).to_be_visible()
    expect(page.locator("div:nth-child(4) > .v-input__control > .v-selection-control > .v-selection-control__wrapper")).to_be_visible()
    highlight_element(page.get_by_label("Side-by-side"), wait).check()
    highlight_element(page.get_by_label("Completed"), wait).check()
    highlight_element(page.get_by_role("button", name="Save"), wait).click()
    highlight_element(page.get_by_role("link", name="Analyze"), wait).click()
    page.reload()
    expect(page.locator("tbody")).to_contain_text("true")
    highlight_element(page.get_by_role("link", name="Publish"), wait).click()
    highlight_element(page.get_by_role("cell", name="Test Product"), wait).click()
    expect(page.locator("tbody")).to_contain_text("complete")
    highlight_element(page.get_by_role("link", name="Assess"), wait).click()
    highlight_element(page.get_by_role("heading", name="Bundesinnenministerin Nancy").first, wait).click()
    highlight_element(page.get_by_role("button", name="ungroup"), wait).click()

    video_path = page.video.path() or None
    context.close()
    browser.close()

    if video_path:
        original_path = video_path
        print(original_path)
        new_path = os.path.join(video_dir, "e2e_test.webm")
        print(new_path)
        os.rename(original_path, new_path)
        print(f"Video saved as: {new_path}")
    else:
        print("No video was recorded.")


@pytest.mark.e2e
def test_e2e_local(news_items):
    with sync_playwright() as playwright:
        run_e2e(
            playwright,
            headless=False,
            wait=2,
            video_dir="videos/",
            viewport={"width": 1920, "height": 1080},
            record_video_size={"width": 1810, "height": 1000},
        )


@pytest.mark.e2e_ci
def test_e2e_ci(news_items):
    with sync_playwright() as playwright:
        run_e2e(playwright)
