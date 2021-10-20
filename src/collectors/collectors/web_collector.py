import datetime
import hashlib
import subprocess
import uuid
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import TimeoutException, NoSuchElementException, InvalidSessionIdException
from urllib.request import urlopen
from bs4 import BeautifulSoup
from collectors.base_collector import BaseCollector
from taranisng.schema.news_item import NewsItemData, NewsItemAttribute
from taranisng.schema.parameter import Parameter, ParameterType
from os import listdir
import os
import socket
from urllib.parse import urlparse
from urllib.error import HTTPError, URLError
from dateutil.parser import parse
import requests
import base64
import re


class WebCollector(BaseCollector):
    type = "WEB_COLLECTOR"
    name = "Web Collector"
    description = "Collector for gathering data from web page"

    parameters = [
        Parameter(0, "WEB_URL", "Web URL", "Full url for web page or folder of html file", ParameterType.STRING),
        Parameter(0, "WEBDRIVER", "Name of Webdriver", "Name of webdriver for selenium", ParameterType.STRING),
        Parameter(0, "TOR", "Do you want to use Tor service? Enter Yes or No", "Using Tor service",
                  ParameterType.STRING),
        Parameter(0, "AUTH_USERNAME", "Username for web page authentication",
                  "Username for authentication with basic auth header", ParameterType.STRING),
        Parameter(0, "AUTH_PASSWORD", "Password for web page authentication",
                  "Password for authentication with basic auth header", ParameterType.STRING),
        Parameter(0, "CLIENT_CERT_DIR", "PATH to directory with client's certificates",
                  "PATH to client's certificates directory", ParameterType.STRING),
        Parameter(0, "USER_AGENT", "User agent", "Set user agent", ParameterType.STRING),
        Parameter(0, "PAGINATION", "Number of pages in pagination to read",
                  "Number of pages in pagination to read.", ParameterType.NUMBER),
        Parameter(0, "NEXT_BUTTON_SELECTOR", "Selector of next button in pagination",
                  "Selector of next button in pagination", ParameterType.STRING),
        Parameter(0, "PARENT_DIRECTORY_SELECTOR", "Parent directory selector",
                  "Selector of node where is article, information", ParameterType.STRING),
        Parameter(0, "TITLE_SELECTOR", "Title selector", "Selector for article or information title",
                  ParameterType.STRING),
        Parameter(0, "DESCRIPTION_SELECTOR", "Description selector",
                  "Selector of article or information description", ParameterType.STRING),
        Parameter(0, "URL_SELECTOR", "Article URL selector", "Selector of full article or information url",
                  ParameterType.STRING),
        Parameter(0, "PUBLISHED_SELECTOR", "Published date selector", "Selector of published date",
                  ParameterType.STRING),
        Parameter(0, "AUTHOR_SELECTOR", "Author selector", "Selector of author", ParameterType.STRING),
        Parameter(0, "ARTICLE_DIV_CLASS_SELECTOR", "Article content DIV class selector",
                  "DIV class_name selector of article content", ParameterType.STRING),
        Parameter(0, "ATTACHMENT_SELECTOR", "Attachment selector", "Selector for article attachment",
                  ParameterType.STRING),
        Parameter(0, "ADDITION_ID_SELECTOR", "Additional ID selector", "Selector of additional ID",
                  ParameterType.STRING),
        Parameter(0, "WORDS_SPLITTING", "Number of words to split content",
                  "Number of words to split content due to legal reason", ParameterType.STRING)
    ]

    parameters.extend(BaseCollector.parameters)

    def collect(self, source):

        news_items = []

        number_of_pages = source.parameter_values['PAGINATION']
        next_button_selector = source.parameter_values['NEXT_BUTTON_SELECTOR']
        parent_directory_selector = source.parameter_values['PARENT_DIRECTORY_SELECTOR']
        title_selector = source.parameter_values['TITLE_SELECTOR']
        description_selector = source.parameter_values['DESCRIPTION_SELECTOR']
        url_selector = source.parameter_values['URL_SELECTOR']
        published_selector = source.parameter_values['PUBLISHED_SELECTOR']
        author_selector = source.parameter_values['AUTHOR_SELECTOR']
        auth_username = source.parameter_values['AUTH_USERNAME']
        auth_password = source.parameter_values['AUTH_PASSWORD']
        attachment_selector = source.parameter_values['ATTACHMENT_SELECTOR']
        additional_id_selector = source.parameter_values['ADDITION_ID_SELECTOR']
        words_splitting = source.parameter_values['WORDS_SPLITTING']
        proxy = source.parameter_values['PROXY_SERVER']
        type_web_driver = source.parameter_values['WEBDRIVER']
        web_url = source.parameter_values['WEB_URL']
        interval = source.parameter_values['REFRESH_INTERVAL']
        user_agent = source.parameter_values['USER_AGENT']
        tor_service = source.parameter_values['TOR']
        client_cert_directory = source.parameter_values['CLIENT_CERT_DIR']

        def configure_chrome_driver():
            chrome_options = ChromeOptions()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--incognito')
            chrome_options.add_argument('user-agent=' + user_agent)
            if tor_service.lower() == 'yes':
                socks_proxy = "socks5://127.0.0.1:9050"
                chrome_options.add_argument('--proxy-server=%s' % socks_proxy)
                driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=chrome_options)
            elif proxy:
                webdriver.DesiredCapabilities.CHROME['proxy'] = {
                    "proxyType": "MANUAL",
                    "httpProxy": proxy,
                    "ftpProxy": proxy,
                    "sslProxy": proxy
                }
                driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=chrome_options)
            else:
                driver = webdriver.Chrome(executable_path='/usr/local/bin/chromedriver', options=chrome_options)
            return driver

        def configure_firefox_driver():
            firefox_options = FirefoxOptions()
            firefox_options.add_argument("--headless")
            firefox_options.add_argument('--ignore-certificate-errors')
            firefox_options.add_argument('--incognito')
            firefox_options.add_argument('user-agent=' + user_agent)
            if tor_service.lower() == 'yes':
                profile = webdriver.FirefoxProfile()
                profile.set_preference('network.proxy.type', 1)
                profile.set_preference('network.proxy.socks', '127.0.0.1')
                profile.set_preference('network.proxy.socks_port', 9050)
                driver = webdriver.Firefox(profile, executable_path='/usr/local/bin/geckodriver',
                                           options=firefox_options)
            elif proxy:
                firefox_capabilities = webdriver.DesiredCapabilities.FIREFOX
                firefox_capabilities['marionette'] = True
                firefox_capabilities['proxy'] = {
                    "proxyType": "MANUAL",
                    "httpProxy": proxy,
                    "ftpProxy": proxy,
                    "sslProxy": proxy
                }
                driver = webdriver.Firefox(executable_path='/usr/local/bin/geckodriver', options=firefox_options,
                                           capabilities=firefox_capabilities)
            else:
                driver = webdriver.Firefox(executable_path='/usr/local/bin/geckodriver', options=firefox_options)
            return driver

        def get_prefix_and_selector(element_selector):
            selector_split = element_selector.split(':', 1)
            prefix = selector_split[0].strip()
            selector = selector_split[1].lstrip()
            return prefix, selector

        def find_element_by(driver, prefix, selector):
            element = ''
            if prefix == 'id':
                element = driver.find_element_by_id(selector)
            if prefix == 'name':
                element = driver.find_element_by_name(selector)
            elif prefix == 'xpath':
                element = driver.find_element_by_xpath(selector)
            elif prefix == 'tag_name':
                element = driver.find_element_by_tag_name(selector)
            elif prefix == 'class_name':
                element = driver.find_element_by_class_name(selector)
            elif prefix == 'css_selector':
                element = driver.find_element_by_css_selector(selector)
            return element

        def find_elements_by(driver, prefix, selector):
            element = ''
            if prefix == 'id':
                element = driver.find_elements_by_id(selector)
            if prefix == 'name':
                element = driver.find_elements_by_name(selector)
            elif prefix == 'xpath':
                element = driver.find_elements_by_xpath(selector)
            elif prefix == 'tag_name':
                element = driver.find_elements_by_tag_name(selector)
            elif prefix == 'class_name':
                element = driver.find_elements_by_class_name(selector)
            elif prefix == 'css_selector':
                element = driver.find_elements_by_css_selector(selector)
            return element

        def collect_data(item):
            new_title_selector_prefix = get_prefix_and_selector(title_selector)[0]
            new_title_selector = get_prefix_and_selector(title_selector)[1]
            title = find_element_by(item, new_title_selector_prefix, new_title_selector).text

            new_description_selector_prefix = get_prefix_and_selector(description_selector)[0]
            new_description_selector = get_prefix_and_selector(description_selector)[1]
            description = find_element_by(item, new_description_selector_prefix, new_description_selector).text

            new_author_selector_prefix = get_prefix_and_selector(author_selector)[0]
            new_author_selector = get_prefix_and_selector(author_selector)[1]
            author = find_element_by(item, new_author_selector_prefix, new_author_selector).text

            new_url_selector_prefix = get_prefix_and_selector(url_selector)[0]
            new_url_selector = get_prefix_and_selector(url_selector)[1]
            link = find_element_by(item, new_url_selector_prefix, new_url_selector).get_attribute('href')

            return title, description, author, link

        def article(soup):
            article_selector = source.parameter_values['ARTICLE_DIV_CLASS_SELECTOR']
            new_article_selector = get_prefix_and_selector(article_selector)[1].replace('.', ' ')
            article_box = soup.find('div', attrs={'class': new_article_selector})
            return article_box

        def attribute(news_item, key, value, binary_mime_type, binary_value):
            news_attribute = NewsItemAttribute(uuid.uuid4(), key, value, binary_mime_type,
                                               binary_value)
            news_item.attributes.append(news_attribute)

        def get_article_content(browser_article, link):
            content = ''
            try:
                browser_article.get(link)
                time.sleep(1)
                html_content = urlopen(link)
                soup = BeautifulSoup(html_content, 'html.parser')
                article_box = article(soup)
                content = [p.text.strip() for p in article_box('p')]

                if content:
                    replaced_str = '\xa0'

                    if replaced_str:
                        content = [w.replace(replaced_str, ' ') for w in content]
                        content = ' '.join(content)

                        number_of_words_in_content = len(content.split())
                        if number_of_words_in_content > words_splitting:
                            content = ' '.join(content.split()[:words_splitting]) + '...'
                        else:
                            splitting = number_of_words_in_content - 5
                            content = ' '.join(content.split()[:splitting]) + '...'

                            print(content)
            except:
                pass
            return content

        def get_images(article_box, news_item):
            img_urls = [img['src'] for img in article_box('img')]
            for url in img_urls:
                key = ''
                value = ''
                binary_mime_type = ''
                binary_value = ''
                try:
                    binary_mime_type = requests.get(url).headers['content-type']
                    binary_value = base64.b64encode(requests.get(url).content).decode('utf-8')
                except requests.exceptions.HTTPError:
                    pass
                except requests.exceptions.MissingSchema:
                    pass
                attribute(news_item, key, value, binary_mime_type, binary_value)

        def get_documents(article_box, news_item):
            a_urls = [a['href'] for a in article_box('a')]
            for url in a_urls:
                key = ''
                value = ''
                binary_mime_type = ''
                binary_value = ''
                filename = re.search(r'/([\w_-]+[.](pdf|docx|xlsx|pptx|odt|ods|odp))$', url)
                if filename:
                    try:
                        binary_mime_type = requests.get(url).headers['content-type']
                        binary_value = base64.b64encode(requests.get(url).content).decode('utf-8')
                    except requests.exceptions.HTTPError:
                        pass
                    except requests.exceptions.MissingSchema:
                        pass
                    attribute(news_item, key, value, binary_mime_type, binary_value)

        def get_additional_id(news_item):
            new_additional_id_selector_prefix = get_prefix_and_selector(additional_id_selector)[0]
            new_additional_id_selector = get_prefix_and_selector(additional_id_selector)[1]
            additional_id = find_element_by(browser, new_additional_id_selector_prefix, new_additional_id_selector).text
            try:
                key = 'Additional_ID'
                value = additional_id
                binary_mime_type = ''
                binary_value = ''

                attribute(news_item, key, value, binary_mime_type, binary_value)
            except:
                pass

        def news_data(title, description, link, published, author, content, attributes):

            for_hash = author + title + description

            news_item = NewsItemData(uuid.uuid4(), hashlib.sha256(for_hash.encode()).hexdigest(),
                                     title, description, web_url, link, published, author,
                                     datetime.datetime.now(), content, source.id, attributes)

            if additional_id_selector:
                get_additional_id(news_item)

            if attachment_selector:
                try:
                    html_content = urlopen(link)
                    soup = BeautifulSoup(html_content, 'html.parser')
                    article_box = article(soup)
                    get_images(article_box, news_item)
                    get_documents(article_box, news_item)
                except:
                    pass

            news_items.append(news_item)

        def get_data():

            try:
                limit = BaseCollector.history(interval)

                for page in range(int(number_of_pages)):
                    new_parent_directory_selector_prefix = get_prefix_and_selector(parent_directory_selector)[0]
                    new_parent_directory_selector = get_prefix_and_selector(parent_directory_selector)[1]
                    article_items = find_elements_by(browser, new_parent_directory_selector_prefix,
                                                     new_parent_directory_selector)

                    for item in article_items:
                        attributes = []
                        if type_web_driver.lower() == 'firefox':
                            browser_article = configure_firefox_driver()
                        else:
                            browser_article = configure_chrome_driver()

                        try:
                            new_published_selector_prefix = get_prefix_and_selector(published_selector)[0]
                            new_published_selector = get_prefix_and_selector(published_selector)[1]
                            published = find_element_by(item, new_published_selector_prefix,
                                                        new_published_selector).text

                            if published:
                                # TODO: make these configurable
                                if published.lower() in [ 'today', 'dnes']:
                                    published = datetime.datetime.today()
                                    published = published.strftime("%d-%m-%Y")
                                    published = parse(published, dayfirst=True)
                                elif published.lower() in [ 'yesterday', 'včera']:
                                    published = datetime.datetime.today() - datetime.timedelta(days=1)
                                    published = published.strftime("%d-%m-%Y")
                                    published = parse(published, dayfirst=True)
                                else:
                                    published = parse(published, dayfirst=True)

                                if published > limit:
                                    title, description, author, link = collect_data(item)

                                    content = get_article_content(browser_article, link)

                                    news_data(title, description, link, published, author, content, attributes)
                            else:
                                for content_page in range(int(number_of_pages)):
                                    published = ''
                                    title, description, author, link = collect_data(item)
                                    content = get_article_content(browser_article, link)

                                    news_data(title, description, link, published, author, content,
                                              attributes)

                            browser_article.close()

                        except Exception as error:
                            BaseCollector.print_exception(source, error)
                            browser_article.close()

                    new_next_button_selector_prefix = get_prefix_and_selector(next_button_selector)[0]
                    new_next_button_selector = get_prefix_and_selector(next_button_selector)[1]
                    find_element_by(browser, new_next_button_selector_prefix, new_next_button_selector).click()

                browser.close()
                BaseCollector.publish(news_items, source)

            except Exception as error:
                BaseCollector.print_exception(source, error)

        if tor_service.lower() == 'yes':
            subprocess.Popen(['tor'])
            time.sleep(3)

        if type_web_driver.lower() == 'firefox':
            browser = configure_firefox_driver()
        else:
            browser = configure_chrome_driver()

        if web_url.startswith('http://') or web_url.startswith('https://'):
            if auth_username and auth_password:
                parsed_url = urlparse(web_url)
                web_url = parsed_url.scheme + '://' + auth_username + ':' + auth_password + '@' + parsed_url.netloc + \
                          parsed_url.path
                response = requests.get(web_url, verify=client_cert_directory)
                if response.status_code == 200:
                    browser.get(web_url)
                    time.sleep(3)
                    get_data()
            else:
                browser.get(web_url)
                response = requests.get(web_url)

                if response.status_code == 200:
                    time.sleep(3)
                    get_data()
        else:
            for file in listdir(web_url):
                if file.endswith('html'):
                    file_name = web_url + file
                    html_file = 'file://' + os.getcwd() + '/' + file_name
                    browser.get(html_file)
                    time.sleep(1)
                    if html_file:
                        get_data()
