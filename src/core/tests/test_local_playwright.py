from playwright.sync_api import Playwright, sync_playwright, expect
import time


def highlight_element_with_css(page, locator, duration):
    # Add a style tag to the head of the document with the highlight style
    style_content = """
    .highlight-element { background-color: yellow; outline: 4px solid red; }
    """
    # style_content = """
    # .highlight-element { outline: 4px solid red; }
    # """

    page.add_style_tag(content=style_content)
    
    # Add the 'highlight-element' class to the element we want to highlight
    locator.evaluate("element => element.classList.add('highlight-element')")
    time.sleep(duration)


def click_with_highlight(locator, duration=2):

    highlight_element_with_css(locator.page, locator, duration)
    
    locator.click()


def test_run(playwright: Playwright) -> None:
    browser = playwright.webkit.launch(headless=False, slow_mo=1000)
    context = browser.new_context(
        storage_state="auth.json",
        record_video_dir="videos/",
        viewport={ 'width': 1920, 'height': 1080 },
        record_video_size={ 'width': 1920, 'height': 1080 }
    )
    # context.tracing.start(name='trace', screenshots=True, snapshots=True)
    page = context.new_page()
    page.goto("http://localhost:8081/")
    page.goto("http://localhost:8081/login")
    click_with_highlight(page.get_by_placeholder("Username"))
    # page.mouse.up()
    # locator.hover()
    # page.mouse.up()
    # page.mouse.down()
    # page.screenshot(path='videos/')
    # locator.click( button='right')
    page.get_by_placeholder("Username").fill("admin")
    # page.get_by_placeholder("Username").press("Tab")
    click_with_highlight(page.get_by_placeholder("Password"))
    page.get_by_placeholder("Password").fill("admin")
    # page.get_by_placeholder("Password").press("Enter")
    # page.get_by_role("link", name="Analyze").first.click()
    # page.get_by_role("button", name="New Report").click()
    # page.get_by_role("button", name="Report Item Type Open").click()
    # page.get_by_text("Vulnerability Report").click()
    # page.get_by_label("Title").click()
    # page.get_by_label("Title").fill("New Report")
    # page.get_by_role("button", name="Save").click()
    # page.get_by_role("link", name="Dashboard").click()
    # page.get_by_role("link", name="Sandworm").click()
    # page.get_by_role("button", name="Expand").nth(2).click()
    # page.get_by_text("Denmark", exact=True).click()
    # page.get_by_role("button", name="reset filter").click()
    # # we can't use week filter for our e2e tests, because that's just irrelevant
    # # page.get_by_role("button", name="week").click()
    # page.get_by_role("button", name="relevance").click()
    # page.get_by_text("a3b89da4ccb998ef9fa66fb11bafcfa1", exact=True).click()
    # page.get_by_role("button", name="add to Report").click()
    # page.get_by_role("button", name="Select Report Open").click()
    # page.get_by_text("New Report").click()
    # page.get_by_role("button", name="share").click()
    # page.get_by_role("link", name="Analyze").click()
    # page.get_by_role("cell", name="New Report").click()
    # page.get_by_role("button", name="Vulnerability", exact=True).click()
    # page.get_by_label("CVE").click()
    # page.get_by_label("CVE").fill("CVE-2021-34473")
    # page.get_by_label("Completed").check()
    # page.get_by_role("button", name="Save").click()
    # page.get_by_role("link", name="Publish").click()
    # page.get_by_role("button", name="New Product").click()
    # page.get_by_role("button", name="Product Type Open").click()
    # page.get_by_text("Default PDF Presenter").click()
    # page.get_by_label("Title").click()
    # page.get_by_label("Title").fill("New Published Item")
    # page.get_by_role("button", name="Create").click()
    # page.get_by_label("Show preview").check()
    # # page.locator("#input-50").check()
    # page.locator("tr:nth-child(2) > td").first.click()
    # page.get_by_role("button", name="Save").click()
    # page.get_by_role("button", name="Render Product").click()
    # page.reload()
    click_with_highlight(page.locator('role=button'))
    # page.get_by_role("button").click()
    # page.screenshot(path="screenshot1.png", full_page=True)
# TODO: next workflow to use
    click_with_highlight(page.locator('role=link[name="Assess"]').first)

    # page.get_by_role("link", name="Assess").first.click()
    # page.screenshot(path="screenshot2.png", full_page=True)
    # page.get_by_role("link", name="Assess").first.click()
    # page.screenshot(path="screenshot3.png", full_page=True)
    # page.get_by_role("link", name="Assess").first.click()
    # page.screenshot(path="screenshot4.png", full_page=True)
    click_with_highlight(page.get_by_role("button", name="relevance"))
    # page.screenshot(path="screenshot5.png", full_page=True)
    click_with_highlight(page.get_by_role("button", name="Expand [12]"))
    click_with_highlight(page.get_by_role("button", name="Collapse [12]"))

    click_with_highlight(page.locator(".v-col-sm-12 > a").first)

    # Scroll the page to the bottom continueously
    last_height = page.evaluate("document.documentElement.scrollHeight")
    current = 0
    while current < last_height:
        # Scroll down by a certain amount
        scroll_pixels = 300
        page.evaluate(f"window.scrollBy(0, {scroll_pixels})")

        # Scroll smoothly
        time.sleep(0.5)

        current += scroll_pixels

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

    # context.tracing.stop(path='test-results/trace.zip')

    # ---------------------
    context.close()
    browser.close()


"""
($ playwright codegen localhost:8081 --save-storage=auth.json)
It might be also a good idea to get a new API token for the {auth.json} when doing it for CI.
($ playwright codegen --load-storage=auth.json localhost:8081)

pg_dump -U taranis taranis > /tmp/e2e_test_db.sql

After every e2e test, the db needs to be reinstantiated.
 docker exec -it dev-database-1 /bin/bash
 cd /usr/local/bin/
 dropdb -U taranis taranis
 createdb -U taranis taranis

 psql -U taranis taranis < /tmp/e2e_test_db.sql
 OR
 pg_restore -U taranis -d taranis /tmp/iktsih_demo_dump.tar
 
 
 
 src/core/tests/conftest.py "def access_token" to generate a token
"""
