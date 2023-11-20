from playwright.sync_api import Playwright, sync_playwright, expect

    # viewport={ "width": 1920, "height": 1080 } , storage_state="auth.json"

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=True, slow_mo=2 * 1000)
    context = browser.new_context(storage_state="auth.json")
    page = context.new_page()
    page.goto("http://localhost:8081/")
    page.goto("http://localhost:8081/login")
    locator = page.get_by_placeholder("Username")
    # page.mouse.up()
    # locator.hover()
    # page.mouse.up()
    # page.mouse.down()
    # page.screenshot(path='videos/')
    # locator.click( button='right')
    page.get_by_placeholder("Username").fill("admin")
    page.get_by_placeholder("Username").press("Tab")
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

    page.get_by_role("button").click()

    page.get_by_role("link", name="Assess").first.click()
    page.get_by_role("button", name="relevance").click()
    page.locator(".v-col-sm-12 > a").first.click()

    page.get_by_role("link", name="Dashboard").click()
    page.get_by_role("link", name="Lazarus Group").click()
    page.get_by_role("button", name="Expand [6]").click()
    page.get_by_text("Spain", exact=True).click()
    page.get_by_role("link", name="open").click()
    page.get_by_role("button", name="add to Report").click()
    page.get_by_role("button", name="Select Report Open").click()
    page.get_by_text("Weekly report").click()
    page.get_by_role("button", name="share").click()
    page.get_by_role("link", name="Analyze").click()
    page.get_by_role("cell", name="Weekly report").click()
    page.get_by_role("button", name="Vulnerability", exact=True).click()
    page.get_by_label("Description").click()
    page.get_by_role("button", name="Open", exact=True).click()
    page.get_by_text("Unauthorized access to the system").click()
    page.get_by_label("Description").click()
    page.get_by_label("Description").fill("Espionage in North Korea")
    # page.get_by_label("Completed").check()
    page.get_by_role("button", name="Save").click()
    page.get_by_role("link", name="Publish").click()
    page.get_by_role("cell", name="Events of the 25th week").click()
    page.get_by_role("button", name="Render Product").click()
    page.reload()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)

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
