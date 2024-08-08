from playwright.sync_api import sync_playwright
from worker.log import logger


class PlaywrightExtension:
    def fetch_content_with_js(self, web_url: str) -> str:
        logger.debug(f"Getting web content with JS for {web_url}")

        self.page.goto(web_url)
        self.page.wait_for_load_state("networkidle")

        return self.page.content() or ""

    def start_playwright_if_needed(self) -> None:
        if self.js_all == "true" or self.js_digest_split == "true":
            self.playwright = sync_playwright().start()
            logger.debug("Playwright started")
            self.setup_browser()

    def setup_browser(self) -> None:
        # TODO: Proxy and user agent support
        if None in self.proxies.values():
            self.browser = self.playwright.chromium.launch()
            logger.debug("Playwright chromium launched")
        else:
            self.browser = self.playwright.chromium.launch(
                proxy={"server": self.proxies["http"]},
            )
        self.page = self.browser.new_page()
        logger.debug("Playwright new page created")


    def stop_playwright_if_needed(self) -> None:
        if self.playwright:
            self.browser.close()
            self.playwright.stop()
