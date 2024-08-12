from playwright.sync_api import sync_playwright, BrowserContext
from urllib.parse import urlparse

from worker.log import logger


class PlaywrightManager:
    def __init__(self, proxies: dict | None = None, headers: dict | None = None) -> None:
        self.playwright = sync_playwright().start()
        self.context = self.setup_context(proxies, headers)
        self.page = self.context.new_page()
        self.browser = None


    def setup_context(self, proxies: dict | None = None, headers: dict | None = None) -> BrowserContext:
        self.browser = self.playwright.chromium.launch(proxy=self.parse_proxies(proxies))
        if None not in headers.values():
            return self.browser.new_context(extra_http_headers=headers)
        return self.browser.new_context()

    def parse_proxies(self, proxies: dict | None = None) -> dict:
        http_proxy = proxies.get("http")
        if not http_proxy:
            return None
        parsed_url = urlparse(http_proxy)
        username = parsed_url.username or ""
        password = parsed_url.password or ""
        logger.debug(f"Setting up proxy with user: {username}")
        return {"server": parsed_url.geturl(), "username": username, "password": password}
    
    def stop_playwright_if_needed(self) -> None:
        if self.playwright:
            self.context.close()
            self.browser.close()
            self.playwright.stop()
            logger.debug("Playwright context stopped")

    def fetch_content_with_js(self, url: str, xpath: str = "") -> str:
        logger.debug(f"Getting web content with JS for {url}")

        self.page.goto(url)

        if xpath:
            locator = self.page.locator(f"xpath={xpath}")
            locator.wait_for(state="visible")
            return self.page.content() or ""

        self.page.wait_for_load_state("networkidle")

        return self.page.content() or ""
