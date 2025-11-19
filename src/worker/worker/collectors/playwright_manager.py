import asyncio
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import BrowserContext as AsyncBrowserContext
from playwright.async_api import TimeoutError as AsyncTimeoutError
from playwright.async_api import async_playwright
from playwright.sync_api import BrowserContext, sync_playwright
from playwright.sync_api import TimeoutError as SyncTimeoutError

from worker.log import logger


class PlaywrightManager:
    def __init__(self, proxies: dict | None = None, headers: dict | None = None) -> None:
        self._async_mode = self._is_async_loop_running()
        self._proxies = proxies
        self._headers = headers

        self.playwright: Any = None
        self.browser: Any = None
        self.context: Any = None
        self.page: Any = None
        self._async_initialized = False

        if not self._async_mode:
            self._initialize_sync()

    def setup_context(self, headers: dict | None = None) -> BrowserContext:
        if headers and None not in headers.values():
            return self.browser.new_context(extra_http_headers=headers)
        return self.browser.new_context()

    async def setup_context_async(self, headers: dict | None = None) -> AsyncBrowserContext:
        if headers and None not in headers.values():
            return await self.browser.new_context(extra_http_headers=headers)
        return await self.browser.new_context()

    def parse_proxies(self, proxies: dict | None = None) -> dict | None:
        http_proxy = proxies.get("http") if proxies else None
        if not http_proxy:
            return None
        parsed_url = urlparse(http_proxy)
        username = parsed_url.username or ""
        password = parsed_url.password or ""
        logger.debug(f"Setting up proxy with user: {username}")
        return {"server": parsed_url.geturl(), "username": username, "password": password}

    def stop_playwright_if_needed(self):
        if self._async_mode:
            self._async_initialized = False

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

        self.page = None

    def fetch_content_with_js(self, url: str, xpath: str = ""):
        logger.debug(f"Getting web content with JS for {url} and {xpath=}")
        if self._async_mode:
            return self._fetch_content_with_js_async(url, xpath)
        return self._fetch_content_with_js_sync(url, xpath)

    def _fetch_content_with_js_sync(self, url: str, xpath: str = "") -> str:
        try:
            self.page.goto(url)

            if xpath:
                locator = self.page.locator(f"xpath={xpath}")
                locator.wait_for(state="visible")
                return self.page.content() or ""

            self.page.wait_for_load_state("networkidle")
        except SyncTimeoutError as e:
            logger.error(
                f"Fetching content with JS for {url} with {xpath=} has timed out, invalid XPath could be the reason, check for details. \nDetails: \n{str(e)}"
            )
        except Exception as e:
            logger.error(f"Error fetching content with JS: {str(e)}")
        return self.page.content() or ""

    async def _fetch_content_with_js_async(self, url: str, xpath: str = "") -> str:
        await self._ensure_async_initialized()
        try:
            await self.page.goto(url)

            if xpath:
                locator = self.page.locator(f"xpath={xpath}")
                await locator.wait_for(state="visible")
                return await self.page.content() or ""

            await self.page.wait_for_load_state("networkidle")
        except AsyncTimeoutError as e:
            logger.error(
                f"Fetching content with JS for {url} with {xpath=} has timed out, invalid XPath could be the reason, check for details. \nDetails: \n{str(e)}"
            )
        except Exception as e:
            logger.error(f"Error fetching content with JS: {str(e)}")
        return await self.page.content() or ""

    def _initialize_sync(self) -> None:
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(proxy=self.parse_proxies(self._proxies))  # type: ignore
        self.context = self.setup_context(self._headers)
        self.page = self.context.new_page()

    async def _ensure_async_initialized(self) -> None:
        if self._async_initialized:
            return
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(proxy=self.parse_proxies(self._proxies))  # type: ignore
        self.context = await self.setup_context_async(self._headers)
        self.page = await self.context.new_page()
        self._async_initialized = True

    def _is_async_loop_running(self) -> bool:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return False
        return loop.is_running()
