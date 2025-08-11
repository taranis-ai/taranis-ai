import pytest
from worker.collectors.playwright_manager import PlaywrightManager


class TestPlaywrightManager:
    def test_playwright_manager_headers(self, playwright_available):
        from worker.tests.testdata import proxies_empty, headers

        pw = PlaywrightManager(proxies=proxies_empty, headers=headers)
        if pw.browser is None:
            pytest.skip("Playwright browser not available in test environment")
        pw.stop_playwright_if_needed()

    def test_playwright_manager_proxies(self, playwright_available):
        from worker.tests.testdata import proxies

        pw = PlaywrightManager(proxies=proxies, headers={})
        if pw.browser is None:
            pytest.skip("Playwright browser not available in test environment")
        pw.stop_playwright_if_needed()

    def test_playwright_manager_header_proxies(self, playwright_available):
        from worker.tests.testdata import proxies, headers

        pw = PlaywrightManager(proxies=proxies, headers=headers)
        if pw.browser is None:
            pytest.skip("Playwright browser not available in test environment")
        pw.stop_playwright_if_needed()

    def test_parse_proxies(self):
        from worker.tests.testdata import proxies, proxy_parse_result
        mgr = PlaywrightManager(proxies=None, headers=None)
        assert mgr.parse_proxies(proxies=proxies) == proxy_parse_result
