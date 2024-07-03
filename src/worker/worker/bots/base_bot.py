from worker.log import logger
from worker.core_api import CoreApi
from urllib.parse import parse_qs
from config import Config
import datetime
import json
import os

class BaseBot:
    def __init__(self):
        self.core_api = CoreApi()
        self.type = "BASE_BOT"
        self.name = "Base Bot"
        self.description = "Base abstract type for all bots"
        self.language = None
        self.models = {}
        self.tokenizers = {}

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

    def load_supported_languages(self):
        supported_languages_path = os.path.join(os.path.dirname(__file__), 'supported_languages.json')
        with open(supported_languages_path, 'r') as file:
            self.supported_languages = json.load(file)

    def initialize_models(self):
        self.models = {}
        self.tokenizers = {}
        for ln in Config.NLP_LANGUAGES:
            if ln in self.supported_languages:
                self.models[ln] = {
                    "SUMMARY_BOT": self.load_model(self.supported_languages[ln]["SUMMARY_BOT"]),
                    "NLP_BOT": self.load_model(self.supported_languages[ln]["NLP_BOT"]),
                    "STORY_BOT": self.load_model(self.supported_languages[ln]["STORY_BOT"])
                }
                self.tokenizers[ln] = {
                    "SUMMARY_BOT": self.load_tokenizer(self.supported_languages[ln]["SUMMARY_BOT"]),
                    "NLP_BOT": self.load_tokenizer(self.supported_languages[ln]["NLP_BOT"]),
                    "STORY_BOT": None  # StoryBot may not need a tokenizer ?
                }

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

    @staticmethod
    def load_tokenizer(model_name):
        from transformers import AutoTokenizer
        return AutoTokenizer.from_pretrained(model_name, use_fast=True)

    def set_language(self, language: str):
        if language not in self.models:
            raise ValueError(f"No models configured for language: {language}")
        self.language = language
        self.model = self.models[language]  # Default model type
        self.tokenizer = self.models[language]  # Default tokenizer type
