from worker.collectors.playwright_manager import PlaywrightManager


class TestPlaywrightManager:
    def test_playwright_manager_headers(self):
        from worker.tests.testdata import proxies_empty, headers

        pw = PlaywrightManager(proxies=proxies_empty, headers=headers)
        pw.stop_playwright_if_needed()

    def test_playwright_manager_proxies(self):
        from worker.tests.testdata import proxies

        pw = PlaywrightManager(proxies=proxies, headers={})
        pw.stop_playwright_if_needed()

    def test_playwright_manager_header_proxies(self):
        from worker.tests.testdata import proxies, headers

        pw = PlaywrightManager(proxies=proxies, headers=headers)
        pw.stop_playwright_if_needed()

    def test_parse_proxies(self):
        from worker.tests.testdata import proxies, proxy_parse_result

        assert PlaywrightManager.parse_proxies(self, proxies=proxies) == proxy_parse_result
