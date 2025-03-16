from playwright.sync_api import sync_playwright, BrowserContext, TimeoutError
from urllib.parse import urlparse

from worker.log import logger


class PlaywrightManager:
    def __init__(self, proxies: dict | None = None, headers: dict | None = None) -> None:
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(proxy=self.parse_proxies(proxies))  # type: ignore
        self.context = self.setup_context(headers)
        self.page = self.context.new_page()

    def setup_context(self, headers: dict | None = None) -> BrowserContext:
        if headers and None not in headers.values():
            return self.browser.new_context(extra_http_headers=headers)
        return self.browser.new_context()

    def parse_proxies(self, proxies: dict | None = None) -> dict | None:
        http_proxy = proxies.get("http") if proxies else None
        if not http_proxy:
            return None
        parsed_url = urlparse(http_proxy)
        username = parsed_url.username or ""
        password = parsed_url.password or ""
        logger.debug(f"Setting up proxy with user: {username}")
        return {"server": parsed_url.geturl(), "username": username, "password": password}

    def stop_playwright_if_needed(self) -> None:
        if self.context:
            self.context.close()
            logger.debug("Playwright context closed")
        else:
            logger.debug("No Playwright context to close")

        if self.browser:
            self.browser.close()
            logger.debug("Playwright browser closed")
        else:
            logger.debug("No Playwright browser to close")

        if self.playwright:
            self.playwright.stop()
            logger.debug("Playwright context stopped")
        else:
            logger.debug("No Playwright to stop")

    def fetch_content_with_js(self, url: str, xpath: str = "") -> str:
        logger.debug(f"Getting web content with JS for {url} and XPATH {xpath=}")
        try:
            self.page.goto(url)

            if xpath:
                locator = self.page.locator(f"xpath={xpath}")
                locator.wait_for(state="visible")
                return self.page.content() or ""

            self.page.wait_for_load_state("networkidle")
        except TimeoutError as e:
            logger.error(
                f"Fetching content with JS for {url} with {xpath=} has timed out, invalid XPath could be the reason, check for details. \nDetails: \n{str(e)}"
            )
        except Exception as e:
            logger.error(f"Error fetching content with JS: {str(e)}")
        return self.page.content() or ""
