import datetime
import hashlib
import uuid
import bleach
import contextlib
import re

from collectors.managers import time_manager
from collectors.managers.log_manager import logger
from collectors.remote.core_api import CoreApi
from shared.schema import collector, osint_source, news_item
from shared.schema.parameter import Parameter, ParameterType


class BaseCollector:
    type = "BASE_COLLECTOR"
    name = "Base Collector"
    description = "Base abstract type for all collectors"

    parameters = [
        Parameter(
            0,
            "PROXY_SERVER",
            "Proxy server",
            "Type SOCKS5 proxy server as username:password@ip:port or ip:port",
            ParameterType.STRING,
        ),
        Parameter(
            0,
            "REFRESH_INTERVAL",
            "Refresh interval in minutes",
            "How often is this collector queried for new data",
            ParameterType.NUMBER,
        ),
    ]

    def __init__(self):
        self.osint_sources = []
        self.core_api = CoreApi()

    def get_info(self):
        info_schema = collector.CollectorSchema()
        return info_schema.dump(self)

    def collect(self, source):
        pass

    @staticmethod
    def print_exception(source, error):
        logger.log_info(f"OSINTSource ID: {source.id}")
        logger.log_info(f"OSINTSource name: {source.name}")
        if str(error).startswith("b"):
            logger.log_info(f"ERROR: {str(error)[2:-1]}")
        else:
            logger.log_info(f"ERROR: {str(error)}")

    @staticmethod
    def history(interval):
        if interval[0].isdigit() and ":" in interval:
            return datetime.datetime.now() - datetime.timedelta(days=1)
        elif interval[0].isalpha():
            return datetime.datetime.now() - datetime.timedelta(weeks=1)
        elif int(interval) > 60:
            hours = int(interval) // 60
            minutes = int(interval) - hours * 60
            return datetime.datetime.now() - datetime.timedelta(days=0, hours=hours, minutes=minutes)

        else:
            return datetime.datetime.now() - datetime.timedelta(days=0, hours=0, minutes=int(interval))

    @staticmethod
    def filter_by_word_list(news_items, source):
        if not source.word_lists:
            return news_items
        one_word_list = set()
        for word_list in source.word_lists:
            if word_list.use_for_stop_words is False:
                for category in word_list.categories:
                    for entry in category.entries:
                        one_word_list.add(entry.value.lower())
        if not one_word_list:
            return news_items
        filtered_news_items = []
        for item in news_items:
            for word in one_word_list:
                if word in item.title.lower() or word in item.review.lower() or word in item.content.lower():
                    filtered_news_items.append(item)
                    break
        return filtered_news_items

    @staticmethod
    def presanitize_html(html):
        # these re.sub are not security sensitive ; bleach is supposed to fix the remaining stuff
        html = re.sub(r"(?i)(&nbsp;|\xa0)", " ", html, re.DOTALL)
        html = re.sub(r"(?i)<head[^>/]*>.*?</head[^>/]*>", "", html, re.DOTALL)
        html = re.sub(r"(?i)<script[^>/]*>.*?</script[^>/]*>", "", html, re.DOTALL)
        html = re.sub(r"(?i)<style[^>/]*>.*?</style[^>/]*>", "", html, re.DOTALL)

        clean = bleach.clean(html, tags=["p", "b", "i", "b", "u", "pre"], strip=True)
        return clean

    @staticmethod
    def sanitize_news_items(news_items, source):
        for item in news_items:
            if item.id is None:
                item.id = uuid.uuid4()
            if item.title is None:
                item.title = ""
            if item.review is None:
                item.review = ""
            if item.source is None:
                item.source = ""
            if item.link is None:
                item.link = ""
            if item.author is None:
                item.author = ""
            if item.content is None:
                item.content = ""
            if item.published is None:
                item.published = datetime.datetime.now()
            if item.collected is None:
                item.collected = datetime.datetime.now()
            if item.hash is None:
                for_hash = item.author + item.title + item.link
                item.hash = hashlib.sha256(for_hash.encode()).hexdigest()
            if item.osint_source_id is None:
                item.osint_source_id = source.id
            if item.attributes is None:
                item.attributes = []
            item.title = BaseCollector.presanitize_html(item.title)
            item.review = BaseCollector.presanitize_html(item.review)
            item.content = BaseCollector.presanitize_html(item.content)
            item.author = BaseCollector.presanitize_html(item.author)
            item.source = BaseCollector.presanitize_html(item.source)  # TODO: replace with link sanitizer
            item.link = BaseCollector.presanitize_html(item.link)  # TODO: replace with link sanitizer

    def publish(self, news_items, source):
        BaseCollector.sanitize_news_items(news_items, source)
        filtered_news_items = BaseCollector.filter_by_word_list(news_items, source)
        news_items_schema = news_item.NewsItemDataSchema(many=True)
        self.core_api.add_news_items(news_items_schema.dump(filtered_news_items))

    def refresh(self):
        logger.log_info(f"Core API requested a refresh of osint sources for {self.type}...")

        # cancel all existing jobs
        # TODO: cannot cancel jobs that are running and are scheduled for further in time than 60 seconds
        # updating of the configuration needs to be done more gracefully
        for source in self.osint_sources:
            with contextlib.suppress(Exception):
                time_manager.cancel_job(source.scheduler_job)
        self.osint_sources = []

        # get new node configuration
        response, code = self.core_api.get_osint_sources(self.type)

        logger.log_debug(f"HTTP {code}: Got the following reply: {response}")

        if code != 200 or response is None:
            return

        try:
            source_schema = osint_source.OSINTSourceSchemaBase(many=True)
            self.osint_sources = source_schema.load(response)

            logger.log_debug(f"{len(self.osint_sources)} data loaded")

            # start collection
            for source in self.osint_sources:
                self.collect(source)
                interval = source.parameter_values["REFRESH_INTERVAL"]

                # do not schedule if no interval is set
                if interval == "":
                    continue

                logger.log_debug("scheduling.....")

                # run task every day at XY
                if interval[0].isdigit() and ":" in interval:
                    source.scheduler_job = time_manager.schedule_job_every_day(interval, self.collect, source)
                elif interval[0].isalpha():
                    interval = interval.split(",")
                    day = interval[0].strip()
                    at = interval[1].strip()
                    if day == "Monday":
                        source.scheduler_job = time_manager.schedule_job_on_monday(at, self.collect, source)
                    elif day == "Tuesday":
                        source.scheduler_job = time_manager.schedule_job_on_tuesday(at, self.collect, source)
                    elif day == "Wednesday":
                        source.scheduler_job = time_manager.schedule_job_on_wednesday(at, self.collect, source)
                    elif day == "Thursday":
                        source.scheduler_job = time_manager.schedule_job_on_thursday(at, self.collect, source)
                    elif day == "Friday":
                        source.scheduler_job = time_manager.schedule_job_on_friday(at, self.collect, source)
                    elif day == "Saturday":
                        source.scheduler_job = time_manager.schedule_job_on_saturday(at, self.collect, source)
                    elif day == "Sunday":
                        source.scheduler_job = time_manager.schedule_job_on_sunday(at, self.collect, source)
                else:
                    logger.log_debug(f"scheduling for {int(interval)}")
                    source.scheduler_job = time_manager.schedule_job_minutes(int(interval), self.collect, source)
        except Exception:
            logger.log_debug_trace()
