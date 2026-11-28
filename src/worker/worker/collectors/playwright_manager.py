import traceback
from urllib.parse import urlparse

from niquests.exceptions import HTTPError, RequestException, Timeout
from playwright.sync_api import Browser, BrowserContext, Error, Page, Playwright, TimeoutError, sync_playwright

from worker.log import logger


class PlaywrightManager:
    def __init__(self, proxies: dict | None = None, headers: dict | None = None) -> None:
        self.proxies = proxies
        self.headers = headers
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def _ensure_started(self) -> None:
        if self.playwright and self.browser and self.context and self.page:
            return

        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(proxy=self.parse_proxies(self.proxies))  # type: ignore
        self.context = self.setup_context(self.headers)
        self.page = self.context.new_page()

    def setup_context(self, headers: dict | None = None) -> BrowserContext:
        if self.browser is None:
            raise RuntimeError("Playwright browser is not started")
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

    def fetch_content_with_js(self, url: str, xpath: str = "") -> tuple[str, str | None]:
        logger.debug(f"Getting web content with JS for {url} - {xpath=}")
        self._ensure_started()
        page = self.page
        if page is None:
            raise RuntimeError("Playwright page is not started")
        last_modified = None
        try:
            response = page.goto(url)
            if response:
                if response.status == 304 or response.status >= 400:
                    raise HTTPError(f"Browser navigation returned HTTP {response.status}")
                last_modified = response.header_value("Last-Modified")

            if xpath:
                page.locator(f"xpath={xpath}").first.wait_for(state="visible")
            else:
                page.wait_for_load_state("networkidle")
            return page.content() or "", last_modified
        except TimeoutError as e:
            logger.error(f"Browser request timed out for {url} with {xpath=}: {e}")
            logger.debug(traceback.format_exc())
            raise Timeout("The browser request timed out. See worker logs for details.") from None
        except Error as e:
            logger.error(f"Error fetching content with JS: {e!s}")
            logger.debug(traceback.format_exc())
            raise RequestException("The browser could not load the page. See worker logs for details.") from None
