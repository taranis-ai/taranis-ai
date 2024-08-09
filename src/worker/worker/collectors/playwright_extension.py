from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

from worker.log import logger


class PlaywrightExtension:
    def start_playwright_if_needed(self) -> None:
        if self.js_all == "true" or self.js_digest_split == "true":
            self.playwright = sync_playwright().start()
            logger.debug("Playwright started")
            self.setup_browser()

    def stop_playwright_if_needed(self) -> None:
        if self.playwright:
            self.browser.close()
            self.playwright.stop()
            logger.debug("Playwright context stopped")

    def setup_browser(self) -> None:
        if None not in self.proxies.values() or self.headers:
            self.start_browser_custom()
        else:
            self.start_browser_basic()

        self.page = self.browser.new_page()
        logger.debug("Playwright new page created")

    def start_browser_basic(self) -> None:
        self.browser = self.playwright.chromium.launch(headless=False)
        logger.debug("Playwright chromium launched")

    def start_browser_custom(self) -> None:
        proxy = None
        if None not in self.proxies.values():
            parsed_url = urlparse(self.proxies["http"])
            username = parsed_url.username or ""
            password = parsed_url.password or ""
            proxy = {"server": self.proxies["http"], "username": username, "password": password}
            logger.debug(f"Playwright chromium launching with a proxy: '{proxy}'")
        
        self.browser = self.playwright.chromium.launch(headless=False, proxy=proxy)
        self.browser.new_context(extra_http_headers=self.headers)
        logger.debug(f"Playwright chromium launching with additional headers: '{self.headers}'")

    def fetch_content_with_js(self, web_url: str) -> str:
        logger.debug(f"Getting web content with JS for {web_url}")

        self.page.goto(web_url)
        self.page.wait_for_load_state("networkidle")
        self.page.pause()

        return self.page.content() or ""
