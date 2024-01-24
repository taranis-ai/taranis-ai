from playwright.sync_api import Playwright, sync_playwright, expect


def test_run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context(storage_state="codegen_api_conf.json", viewport={"width": 1920, "height": 1080})
    # context.tracing.start(name='trace', screenshots=True, snapshots=True)
    page = context.new_page()
    page.goto("http://localhost:8081/")
    page.goto("http://localhost:8081/login")

    page.get_by_placeholder("Username").fill("admin")
    page.get_by_placeholder("Username").press("Tab")
    page.get_by_placeholder("Password").fill("admin")
    page.get_by_role("button").click()

    page.screenshot(path="screenshot1.png", full_page=True)

    # One of the problematic buttons in CI
    page.get_by_role("link", name="Assess").first.click()
    page.screenshot(path="screenshot2.png", full_page=True)
    # page.get_by_role("link", name="Assess").first.click()
    # page.screenshot(path="screenshot3.png", full_page=True)
    # page.get_by_role("link", name="Assess").first.click()
    # page.screenshot(path="screenshot4.png", full_page=True)
    # page.get_by_role("button", name="relevance").click()
    # page.screenshot(path="screenshot5.png", full_page=True)
    # page.locator(".v-col-sm-12 > a").first.click()

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
    # page.get_by_label("Completed").check() # Something was inconsistent with this action
    page.get_by_role("button", name="Save").click()
    page.get_by_role("link", name="Publish").click()
    page.get_by_role("cell", name="Events of the 25th week").click()
    page.get_by_role("button", name="Render Product").click()
    page.reload()

    # context.tracing.stop(path='test-results/trace.zip')

    # ---------------------
    context.close()
    browser.close()
