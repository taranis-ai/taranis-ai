from .base_bot import BaseBot
from shared.schema.parameter import Parameter, ParameterType
from bots.managers.log_manager import logger
import datetime


class TaggingBot(BaseBot):
    type = "TAGGING_BOT"
    name = "Tagging Bot"
    description = "Bot for tagging news items"

    parameters = [
        Parameter(
            0,
            "SOURCE_GROUP",
            "Source Group",
            "OSINT Source group to inspect",
            ParameterType.STRING,
        ),
        Parameter(
            0,
            "KEYWORDS",
            "Keywords",
            "Keywords to Tag on seperated by ','",
            ParameterType.STRING,
        ),
    ]
    parameters.extend(BaseBot.parameters)

    def execute(self, preset):
        try:
            source_group = preset.parameter_values["SOURCE_GROUP"]
            interval = preset.parameter_values["REFRESH_INTERVAL"]
            keywords = preset.parameter_values["KEYWORDS"].split(",")

            limit = BaseBot.history(interval)
            limit = datetime.datetime.now() - datetime.timedelta(weeks=12)
            logger.log_debug(f"LIMIT: {limit}")
            logger.log_debug(f"KEYWORDKS: {keywords}")

            data, status = self.core_api.get_news_items_aggregate(source_group, limit)
            if status != 200:
                return

            if data:
                for aggregate in data:
                    findings = {}
                    for news_item in aggregate["news_items"]:
                        content = news_item["news_item_data"]["content"]
                        existing_tags = news_item["news_item_data"]["tags"] if news_item["news_item_data"]["tags"] is not None else []

                        for keyword in keywords:
                            if keyword in content and keyword not in existing_tags:
                                if news_item["id"] in findings:
                                    findings[news_item["id"]] = findings[news_item["id"]].add(keyword)
                                else:
                                    findings[news_item["id"]] = {keyword}
                    for news_id, keyword in findings.items():
                        logger.log_debug(f"news_id: {news_id}, keyword: {keyword}")
                        if keyword is None:
                            continue
                        self.core_api.update_news_item_tags(news_id, list(keyword))

        except Exception as error:
            BaseBot.print_exception(preset, error)

    def execute_on_event(self, preset, event_type, data):
        try:
            # source_group = preset.parameter_values["SOURCE_GROUP"]
            # keywords = preset.parameter_values["KEYWORDS"]
            pass
        except Exception as error:
            BaseBot.print_exception(preset, error)
