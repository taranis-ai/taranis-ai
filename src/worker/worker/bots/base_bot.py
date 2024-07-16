from worker.log import logger
from worker.core_api import CoreApi
from urllib.parse import parse_qs
from worker.config import Config
import datetime


class BaseBot:
    def __init__(self):
        self.core_api = CoreApi()
        self.type = "BASE_BOT"
        self.name = "Base Bot"
        self.description = "Base abstract type for all bots"
        self.language = None
        self.model = None

    def execute(self):
        pass

    def get_filter_dict(self, parameters) -> dict:
        filter_dict = {}
        if item_filter := parameters.pop("ITEM_FILTER", None):
            filter_dict = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(item_filter).items()}

        if param_filter := parameters.get("filter"):
            filter_dict |= {k.lower(): v for k, v in param_filter.items()}

        if "story_id" in filter_dict:
            return filter_dict

        if "timefrom" not in filter_dict:
            limit = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
            filter_dict["timefrom"] = limit

        filter_dict["no_count"] = True
        filter_dict["exclude_attr"] = self.type

        return filter_dict

    def update_filter_for_pagination(self, filter_dict, limit=100):
        filter_dict["limit"] = limit
        if "offset" in filter_dict:
            filter_dict["offset"] += limit
        else:
            filter_dict["offset"] = limit
        return filter_dict

    def get_stories(self, parameters) -> list:
        filter_dict = self.get_filter_dict(parameters)
        data = self.core_api.get_stories(filter_dict)
        if not data:
            logger.debug(f"No Stories for filter: {filter_dict}")
        return data

    def refresh(self):
        logger.info(f"Refreshing Bot: {self.type} ...")
        self.execute()

    def initialize_models(self):
        if self.language not in Config.LANGUAGE_MODEL_MAPPING:
            logger.error(f"Language {self.language} not found in configuration.")
            return

        model_mapping = Config.LANGUAGE_MODEL_MAPPING[self.language]

        if self.type == "STORY_BOT":
            if "STORY_BOT" in model_mapping:
                self.model = self.load_model(model_mapping["STORY_BOT"])
                self.tokenizer = self.load_tokenizer(model_mapping["STORY_BOT"])
            else:
                logger.error("STORY_BOT model not found in configuration for the given language.")
        elif self.type == "SUMMARY_BOT":
            if "SUMMARY_BOT" in model_mapping:
                self.model = self.load_model(model_mapping["SUMMARY_BOT"])
                self.tokenizer = self.load_tokenizer(model_mapping["SUMMARY_BOT"])
            else:
                logger.error("SUMMARY_BOT model not found in configuration for the given language.")
        elif self.type == "NLP_BOT":
            if "NLP_BOT" in model_mapping:
                self.model = self.load_classifier(model_mapping["NLP_BOT"])
            else:
                logger.error("NLP_BOT model not found in configuration for the given language.")
        else:
            logger.error(f"Unknown bot type: {self.type}")

    @staticmethod
    def load_classifier(model_name):
        from flair.nn import Classifier

        return Classifier.load(model_name)

    @staticmethod
    def load_model(model_name):
        from transformers import AutoModelForSeq2SeqLM, AutoModel
        from sentence_transformers import SentenceTransformer

        if "bart" in model_name or "t5" in model_name:  # Example model types
            return AutoModelForSeq2SeqLM.from_pretrained(model_name)
        elif "sentence-transformers" in model_name:  # For SentenceTransformer models
            return SentenceTransformer(model_name)
        else:
            return AutoModel.from_pretrained(model_name)

    def load_tokenizer(self, model_name):
        from transformers import AutoTokenizer

        return AutoTokenizer.from_pretrained(model_name, use_fast=True)
