import datetime
import hashlib
import subprocess
import uuid
import time
import copy
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException, InvalidSessionIdException

from urllib.parse import urlparse
from urllib.error import HTTPError, URLError

import os
import dateparser
import base64
import re
from taranisng.managers import log_manager

from collectors.base_collector import BaseCollector
from taranisng.schema.news_item import NewsItemData, NewsItemAttribute
from taranisng.schema.parameter import Parameter, ParameterType

import traceback

class WebCollector(BaseCollector):
    type = "WEB_COLLECTOR"
    name = "Web Collector"
    description = "Collector for gathering data from web page"

    parameters = [
        # base parameters
        Parameter(0, "WEB_URL", "Web URL", "Full url for web page or folder of html file", ParameterType.STRING),

        # browser options

        # TODO: implement ENUM
        Parameter(0, "WEBDRIVER", "Name of Webdriver", "Name of webdriver for Selenium (chrome|firefox)", ParameterType.STRING),
        # TODO: change to BOOLEAN, implement defaults, default False
        Parameter(0, "TOR", "Do you want to use Tor service? Enter Yes or No", "Using Tor service (yes|no)",
                  ParameterType.STRING),
        Parameter(0, "USER_AGENT", "User agent", "Set user agent", ParameterType.STRING),

        # authentication options

        Parameter(0, "AUTH_USERNAME", "Username for web page authentication",
                  "Username for authentication with basic auth header", ParameterType.STRING),
        Parameter(0, "AUTH_PASSWORD", "Password for web page authentication",
                  "Password for authentication with basic auth header", ParameterType.STRING),
        # TODO reimplement for new web collector
        Parameter(0, "CLIENT_CERT_DIR", "PATH to directory with client's certificates",
                  "PATH to client's certificates directory", ParameterType.STRING),

        # web page parsing options

        ## navigating the list of articles page by page
        Parameter(0, "NEXT_BUTTON_SELECTOR", "SELECTOR at TITLE PAGE: Next page",
                  "OPTIONAL: For sites with pagination, this is a selector of the clickable element (button or a link) for the 'next page'", ParameterType.STRING),
        Parameter(0, "LOAD_MORE_BUTTON_SELECTOR", "SELECTOR at TITLE PAGE: Load more",
                  "OPTIONAL: For sites with progressive loading, this is a selector of the clickable element (button or a link) for the 'load more'", ParameterType.STRING),
        Parameter(0, "PAGINATION_LIMIT", "Pagination limit",
                  "OPTIONAL: For sites with pagination or progressive loading, maximum number of pages to visit. Default: 1 (stay on the first page only)", ParameterType.NUMBER),

        ## obtaining links to articles (optional)
        Parameter(0, "SINGLE_ARTICLE_LINK_SELECTOR", "SELECTOR at TITLE PAGE: Links to articles",
                  "Selector that matches the link to the article. Matching results should contain a 'href' attribute.", ParameterType.STRING),

        ## parsing a single article
        Parameter(0, "TITLE_SELECTOR", "SELECTOR at ARTICLE: Article title",
                  "Selector for article title", ParameterType.STRING),
        Parameter(0, "ARTICLE_DESCRIPTION_SELECTOR", "SELECTOR at ARTICLE: short summary",
                  "OPTIONAL: Selector of article description or summary", ParameterType.STRING),
        Parameter(0, "ARTICLE_FULL_TEXT_SELECTOR", "SELECTOR at ARTICLE: Article content",
                  "Selector for the article content / text of the article", ParameterType.STRING),
        Parameter(0, "AUTHOR_SELECTOR", "SELECTOR at ARTICLE: Author",
                  "OPTIONAL: Selector to find the author of the post", ParameterType.STRING),
        Parameter(0, "PUBLISHED_SELECTOR", "SELECTOR at ARTICLE: Date published",
                  "OPTIONAL: Selector of the 'published' date", ParameterType.STRING),
        # TODO reimplement for new web collector
        Parameter(0, "ATTACHMENT_SELECTOR", "SELECTOR at ARTICLE: Attachment selector",
                  "OPTIONAL: Selector for links to article attachments", ParameterType.STRING),

        Parameter(0, "WORD_LIMIT", "Limit article body to this many words",
                  "Collect only first few words of the article (perhaps for legal reasons)", ParameterType.STRING),

        ## legacy options, to be studied in more detail or removed
        Parameter(0, "ADDITIONAL_ID_SELECTOR", "SELECTOR at ARTICLE: Additional ID selector",
                  "OPTIONAL: Selector of an additional article ID", ParameterType.STRING),
    ]
    parameters.extend(BaseCollector.parameters)

    # helper: parse the selector
    @staticmethod
    def __get_prefix_and_selector(element_selector):
        selector_split = element_selector.split(':', 1)
        prefix = selector_split[0].strip().lower()
        selector = selector_split[1].lstrip()
        return prefix, selector

    # extract element from the headless browser by selector
    @staticmethod
    def __find_element_by(driver, element_selector):
        """extracts single element from the headless browser by selector"""

        prefix, selector = WebCollector.__get_prefix_and_selector(element_selector)

        element = None
        if prefix == 'id':
            element = driver.find_element_by_id(selector)
        if prefix == 'name':
            element = driver.find_element_by_name(selector)
        elif prefix == 'xpath':
            element = driver.find_element_by_xpath(selector)
        elif prefix in [ 'tag_name', 'tag' ]:
            element = driver.find_element_by_tag_name(selector)
        elif prefix in [ 'class_name', 'class' ]:
            element = driver.find_element_by_class_name(selector)
        elif prefix in [ 'css_selector', 'css' ]:
            element = driver.find_element_by_css_selector(selector)

        return element

    @staticmethod
    def __find_elements_by(driver, element_selector):
        """extracts list of elements from the headless browser by selector"""

        prefix, selector = WebCollector.__get_prefix_and_selector(element_selector)
        #log_manager.log_debug(driver.page_source)

        elements = None
        if prefix == 'id':
            elements = [ driver.find_element_by_id(selector) ]
        if prefix == 'name':
            elements = driver.find_elements_by_name(selector)
        elif prefix == 'xpath':
            elements = driver.find_elements_by_xpath(selector)
        elif prefix in [ 'tag_name', 'tag' ]:
            elements = driver.find_elements_by_tag_name(selector)
        elif prefix in [ 'class_name', 'class' ]:
            elements = driver.find_elements_by_class_name(selector)
        elif prefix in [ 'css_selector', 'css' ]:
            elements = driver.find_elements_by_css_selector(selector)
        return elements

    @staticmethod
    def __element_text(element):
        if element:
            return element.text
        return ''

    @staticmethod
    def __smart_truncate(content, length=500, suffix='...'):
        if len(content) <= length:
            return content
        else:
            return ' '.join(re.compile(r'\s+').split(content[:length+1])[0:-1]) + suffix

    @staticmethod
    def __wait_for_new_tab(browser, timeout, current_tab):
        yield
        WebDriverWait(browser, timeout).until(
            lambda browser: len(handles_before) != 1
        )
        for tab in browser.window_handles:
            if tab != current_tab:
                browser.switch_to.window(tab)
                return


    @staticmethod
    def __close_other_tabs(browser, handle_to_keep, fallback_url):
        try:
            handles_to_close = copy.copy(browser.window_handles)
            for handle_to_close in handles_to_close:
                if handle_to_close != handle_to_keep:
                    browser.switch_to.window(handle_to_close)
                    browser.close()
                    #time.sleep(1)
                if len(browser.window_handles) == 1:
                    break
            browser.switch_to.window(handle_to_keep)
        except:
            log_manager.log_collector_activity('web', self.source.id, 'Browser tab restoration failed, reloading the title page')
            try:
                # last resort - at least try to reopen the original page
                browser.get(fallback_url)
                return True
            except:
                return False
        return (browser.current_window_handle == handle_to_keep)

    # parse settings
    def __parse_settings(self):
        """Loads the collector settings to instance variables"""

        self.auth_username = self.source.parameter_values['AUTH_USERNAME']
        self.auth_password = self.source.parameter_values['AUTH_PASSWORD']

        # parse the URL
        web_url = self.source.parameter_values['WEB_URL']

        if web_url.lower().startswith('file://'):
            file_part = web_url[7:]
            if os.path.isfile(file_part):
                self.interpret_as = 'uri'
                self.web_url = 'file://' + file_part

            elif os.path.isdir(file_part):
                self.interpret_as = 'directory'
                self.web_url = file_part

            else:
                log_manager.log_collector_activity('web', self.source.id, 'Missing file {}'.format(web_url))
                return False

        elif re.search(r'^[a-z0-9]+://', web_url.lower()):
            self.interpret_as = 'uri'
            self.web_url = web_url

        elif os.path.isfile(web_url):
            self.interpret_as = 'uri'
            self.web_url = 'file://' + web_url

        elif os.path.isdir(web_url):
                self.interpret_as = 'directory'
                self.web_url = web_url

        else:
            self.interpret_as = 'uri'
            self.web_url = 'https://' + web_url

        if self.interpret_as == 'uri' and self.auth_username and self.auth_password:
                parsed_url = urlparse(self.web_url)
                self.web_url = "{}://{}:{}@{}{}".format(
                                parsed_url.scheme,
                                self.auth_username,
                                self.auth_password,
                                parsed_url.netloc,
                                parsed_url.path
                )

        # parse other arguments
        self.user_agent = self.source.parameter_values['USER_AGENT']
        self.tor_service = self.source.parameter_values['TOR']

        #self.interval = self.source.parameter_values['REFRESH_INTERVAL']

        try:
            self.pagination_limit = int(self.source.parameter_values['PAGINATION_LIMIT'])
        except:
            self.pagination_limit = 1
        if self.pagination_limit <= 0:
            self.pagination_limit = 1

        self.selectors = {}

        self.selectors['next_page'] = self.source.parameter_values['NEXT_BUTTON_SELECTOR']
        self.selectors['load_more'] = self.source.parameter_values['LOAD_MORE_BUTTON_SELECTOR']
        self.selectors['single_article_link'] = self.source.parameter_values['SINGLE_ARTICLE_LINK_SELECTOR']

        self.selectors['title'] = self.source.parameter_values['TITLE_SELECTOR']
        self.selectors['article_description'] = self.source.parameter_values['ARTICLE_DESCRIPTION_SELECTOR']
        self.selectors['article_full_text'] = self.source.parameter_values['ARTICLE_FULL_TEXT_SELECTOR']
        self.selectors['published'] = self.source.parameter_values['PUBLISHED_SELECTOR']
        self.selectors['author'] = self.source.parameter_values['AUTHOR_SELECTOR']
        self.selectors['attachment'] = self.source.parameter_values['ATTACHMENT_SELECTOR']
        self.selectors['additional_id'] = self.source.parameter_values['ADDITIONAL_ID_SELECTOR']

        try:
            self.word_limit = int(self.source.parameter_values['WORD_LIMIT'])
            if self.word_limit < 0:
                self.word_limit = 0
        except:
            self.word_limit = 0

        self.web_driver_type = self.source.parameter_values['WEBDRIVER']
        self.client_cert_directory = self.source.parameter_values['CLIENT_CERT_DIR']

        self.proxy = ''
        param_proxy = self.source.parameter_values['PROXY_SERVER']
        if re.search(r'^(https?|socks[45])://', param_proxy.lower()):
            self.proxy = param_proxy
        elif re.search(r'^.*:\d+$/', param_proxy.lower()):
            self.proxy = 'http://' + param_proxy

        return True

    def __get_headless_driver_chrome(self):
        """Initializes and returns Chrome driver"""

        chrome_options = ChromeOptions()
        chrome_options.page_load_strategy = 'normal' # .get() returns on document ready
        chrome_options.add_argument("--headless")
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--incognito')
        if self.user_agent:
            chrome_options.add_argument('user-agent=' + self.user_agent)
        if self.tor_service.lower() == 'yes':
            socks_proxy = "socks5://127.0.0.1:9050"
            chrome_options.add_argument('--proxy-server={}'.format(socks_proxy))
            driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=chrome_options)
        elif self.proxy:
            webdriver.DesiredCapabilities.CHROME['proxy'] = {
                "proxyType": "MANUAL",
                "httpProxy": self.proxy,
                "ftpProxy": self.proxy,
                "sslProxy": self.proxy
            }
            driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=chrome_options)
        else:
            driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=chrome_options)
        return driver

    def __get_headless_driver_firefox(self):
        """Initializes and returns Firefox driver"""

        firefox_options = FirefoxOptions()
        firefox_options.page_load_strategy = 'normal' # .get() returns on document ready
        firefox_options.add_argument("--headless")
        firefox_options.add_argument('--ignore-certificate-errors')
        firefox_options.add_argument('--incognito')
        if self.user_agent:
            firefox_options.add_argument('user-agent=' + self.user_agent)
        if self.tor_service.lower() == 'yes':
            profile = webdriver.FirefoxProfile()
            profile.set_preference('network.proxy.type', 1)
            profile.set_preference('network.proxy.socks', '127.0.0.1')
            profile.set_preference('network.proxy.socks_port', 9050)
            driver = webdriver.Firefox(profile, executable_path='/usr/local/bin/geckodriver',
                                       options=firefox_options)
        elif self.proxy:
            firefox_capabilities = webdriver.DesiredCapabilities.FIREFOX
            firefox_capabilities['marionette'] = True
            firefox_capabilities['proxy'] = {
                "proxyType": "MANUAL",
                "httpProxy": self.proxy,
                "ftpProxy": self.proxy,
                "sslProxy": self.proxy
            }
            driver = webdriver.Firefox(executable_path='/usr/local/bin/geckodriver', options=firefox_options,
                                       capabilities=firefox_capabilities)
        else:
            driver = webdriver.Firefox(executable_path='/usr/local/bin/geckodriver', options=firefox_options)
        return driver

    def __get_headless_driver(self):
        """Initializes and returns a headless browser driver"""

        try:
            if self.web_driver_type.lower() == 'firefox':
                browser = self.__get_headless_driver_firefox()
            else:
                browser = self.__get_headless_driver_chrome()
            browser.implicitly_wait(15) # how long to wait for elements when selector doesn't match
            return browser
        except:
            return None

    def __dispose_of_headless_driver(self, driver):
        """Destroys the headless browser driver, and its browser"""
        try:
            driver.close()
        except:
            pass
        try:
            driver.quit()
        except:
            pass
        try:
            driver.dispose()
        except:
            pass

    def __run_tor(self):
        """Runs The Onion Router service in a subprocess"""

        log_manager.log_collector_activity('web', self.source.id, 'Initializing TOR')
        subprocess.Popen(['tor'])
        time.sleep(3)

    def collect(self, source):
        """Collects news items from this source (main function)"""

        self.source = source
        log_manager.log_collector_activity('web', self.source.id, 'Starting collector')

        self.__parse_settings()
        self.news_items = []

        if self.tor_service.lower() == 'yes':
            self.__run_tor()


        if self.interpret_as == "uri":
            result, message, total_processed_articles, total_failed_articles = self.__browse_title_page(self.web_url)

        elif self.interpret_as == "directory":
            log_manager.log_collector_activity('web', self.source.id, 'Searching for html files in {}'.format(self.web_url))
            for file in os.listdir(self.web_url):
                if file.lower().endswith('.html'):
                    html_file = 'file://' + self.web_url + '/' + file_name
                    result, message = self.__browse_title_page(html_file)

    def __browse_title_page(self, index_url):
        """Spawns a browser, downloads the title page for parsing, calls parser."""

        browser = self.__get_headless_driver()
        if browser is None:
            log_manager.log_collector_activity('web', self.source.id, 'Error initialising the headless browser')
            return False, 'Error initialising the headless browser', 0, 0

        log_manager.log_collector_activity('web', self.source.id, 'Requesting title page: {}'.format(self.web_url))
        try:
            browser.get(index_url)
            log_manager.log_collector_activity('web', self.source.id, 'Title page obtained')
        except:
            log_manager.log_collector_activity('web', self.source.id, 'Error obtaining title page')
            self.__dispose_of_headless_driver(browser)
            return False, 'Error obtaining title page', 0, 0

        # if there is a "load more" selector, click on it!
        page = 1
        while self.selectors['load_more'] and page < self.pagination_limit:
            try:
                load_more = self.__find_element_by(browser, self.selectors['load_more'])
                # TODO: check for None
                load_more.click()
                ActionChains(browser) \
                    .move_to_element(load_more) \
                    .click(load_more) \
                    .perform()
                time.sleep(1) # is there a better way?
            except:
                break
            page += 1

        title_page_handle = browser.current_window_handle
        total_processed_articles, total_failed_articles = 0, 0
        while True:
            try:
                processed_articles, failed_articles = self.__process_title_page_articles(browser, title_page_handle, index_url)

                total_processed_articles += processed_articles
                total_failed_articles += failed_articles

                # safety cleanup
                if not self.__close_other_tabs(browser, title_page_handle, fallback_url = index_url):
                    log_manager.log_collector_activity('web', self.source.id, 'Error during page crawl (after-crawl clean up)')
                    break
            except:
                log_manager.log_collector_activity('web', self.source.id, 'Error during page crawl (exception)')
                log_manager.log_debug(traceback.format_exc())
                break

            if page >= self.pagination_limit or not self.selectors['next_page']:
                log_manager.log_collector_activity('web', self.source.id, 'Page limit reached')
                break

            # visit next page of results
            page += 1
            log_manager.log_collector_activity('web', self.source.id, 'Clicking "next page"')
            try:
                next_page = self.__find_element_by(browser, self.selectors['next_page'])
                # TODO: check for None
                ActionChains(browser) \
                    .move_to_element(next_page) \
                    .click(next_page) \
                    .perform()
            except:
                log_manager.log_collector_activity('web', self.source.id, 'This was the last page')
                break

        self.__dispose_of_headless_driver(browser)
        log_manager.log_collector_activity('web', self.source.id, 'Committing {} news items'.format(len(self.news_items)))
        BaseCollector.publish(self.news_items, self.source)

        return True, '', total_processed_articles, total_failed_articles

    def __process_title_page_articles(self, browser, title_page_handle, index_url):
        """Parses the title page for articles"""

        processed_articles, failed_articles = 0, 0

        article_items = self.__find_elements_by(browser, self.selectors['single_article_link'])
        if article_items is None:
            log_manager.log_collector_activity('web', self.source.id, 'Incorrect selector for article items')
            return 0, 0

        index_url_just_before_click = browser.current_url

        for item in article_items:
            try:
                href = item.get_attribute('href')
                log_manager.log_collector_activity('web', self.source.id, 'Visiting article at {}'.format(href))
            except:
                href = ''
                log_manager.log_collector_activity('web', self.source.id, 'Visiting article with no link'.format(href))
            click_method = 1 # TODO: some day, make this user-configurable with tri-state enum

            if click_method == 1:
                link = item.get_attribute('href')
                browser.switch_to.new_window('tab')
                browser.get(link)
            elif click_method == 2:
                browser.move_to_element(item)
                ActionChains(browser) \
                    .key_down(Keys.CONTROL) \
                    .click(item) \
                    .key_up(Keys.CONTROL) \
                    .perform()
                self.__wait_for_new_tab(browser, 15, title_page_handle)
            elif click_method == 3:
                browser.move_to_element(item)
                item.send_keys(Keys.CONTROL + Keys.RETURN)
                self.__wait_for_new_tab(browser, 15, title_page_handle)
            time.sleep(1)

            try:
                news_item = self.__process_article_page(index_url, browser)
                if news_item:
                    log_manager.log_collector_activity('web', self.source.id, 'Successfully parsed an article')
                    self.news_items.append(news_item)
                else:
                    log_manager.log_collector_activity('web', self.source.id, 'Failed to parse an article')
            except:
                success = False
                log_manager.log_collector_activity('web', self.source.id, 'Failed to parse an article (exception)')
                log_manager.log_debug(traceback.format_exc())

            if len(browser.window_handles) == 1:
                back_clicks = 1
                while browser.current_url != index_url_just_before_click:
                    browser.back()
                    back_clicks += 1
                    if back_clicks > 3:
                        log_manager.log_collector_activity('web', self.source.id, 'Error during page crawl (cannot restore window after crawl)')
            elif not self.__close_other_tabs(browser, title_page_handle, fallback_url = index_url):
                log_manager.log_collector_activity('web', self.source.id, 'Error during page crawl (after-crawl clean up)')
                break
        return processed_articles, failed_articles

    def __process_article_page(self, index_url, browser):
        """Parses a single article"""

        current_url = browser.current_url

        log_manager.log_collector_activity('web', self.source.id, 'Processing article page: {}'.format(current_url))

        title = self.__element_text(self.__find_element_by(browser, self.selectors['title']))

        article_full_text = self.__element_text(self.__find_element_by(browser, self.selectors['article_full_text']))
        if self.word_limit > 0:
            article_full_text = ' '.join(re.compile(r'\s+').split(article_full_text)[:self.word_limit])

        if self.selectors['article_description']:
            article_description = self.__element_text(self.__find_element_by(browser, self.selectors['article_description']))
        else:
            article_description = ''
        if self.word_limit > 0:
            article_description = ' '.join(re.compile(r'\s+').split(article_description)[:self.word_limit])
        if not article_description:
            article_description = self.__smart_truncate(article_full_text)

        published_str = self.__element_text(self.__find_element_by(browser, self.selectors['published']))
        if not published_str:
            published_str = 'today'
        published = dateparser.parse(published_str, settings={'DATE_ORDER': 'DMY'})

        link = current_url

        author = self.__element_text(self.__find_element_by(browser, self.selectors['author']))

        for_hash = author + title + article_description
        news_item = NewsItemData(
                        uuid.uuid4(),
                        hashlib.sha256(for_hash.encode()).hexdigest(),
                        title, article_description,
                        self.web_url, link,
                        published,
                        author,
                        datetime.datetime.now(),
                        article_full_text,
                        self.source.id,
                        []
        )

        if self.selectors['additional_id']:
            value = self.__element_text(self.__find_element_by(browser, self.selectors['additional_id']))
            if value:
                key = 'Additional_ID'
                binary_mime_type = ''
                binary_value = ''
                attribute = NewsItemAttribute(uuid.uuid4(), key, value, binary_mime_type, binary_value)
                news_item.attributes.append(attribute)
        return news_item
