from .base_bot import BaseBot
from worker.log import logger
import datetime
import spacy, spacy.cli
import py3langid
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from polyfuzz import PolyFuzz
from polyfuzz.models import TFIDF
from sentence_transformers import SentenceTransformer
from keybert import KeyBERT
import numpy
from pandas import DataFrame
import nltk
import torch

class NLPBot(BaseBot):
    type = "NLP_BOT"
    name = "NLP Bot"
    description = "Bot for naturale language processing of news items"

    def __init__(self):
        super().__init__()
        logger.debug("Setup NER Model...")
        self.ner_model = spacy.load("xx_ent_wiki_sm")
        torch.set_num_threads(1) # https://github.com/pytorch/pytorch/issues/36191
        self.polyfuzz_model = PolyFuzz(TFIDF(model_id="TF-IDF", clean_string=False, n_gram_range=(3, 3), min_similarity=0))
        self.keybert_model = KeyBERT(model=SentenceTransformer("basel/ATTACK-BERT"))
        self.wordnet_lemmatizer = WordNetLemmatizer()
        nltk.download('wordnet')
        self.language = ""
        self.extraction_text_limit = 5000

    def execute(self, parameters=None):
        if not parameters:
            return
        try:
            source_group = parameters.get("SOURCE_GROUP")
            source = parameters.get("SOURCE")

            limit = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
            filter_dict = {"timestamp": limit}
            if source_group:
                filter_dict["source_group"] = source_group
            if source:
                filter_dict["source"] = source

            data = self.core_api.get_news_items_aggregate(filter_dict)
            if not data:
                logger.critical("Error getting news items")
                return

            all_keywords = {} # TODO: Extract existing keywords from news items
            for aggregate in data:
                current_keywords = aggregate.get("tags", {})
                aggregate_content = ""

                for news_item in aggregate["news_items"]:
                    content = (
                        news_item["news_item_data"]["content"] + news_item["news_item_data"]["review"] + news_item["news_item_data"]["title"]
                    )
                    aggregate_content += content

                    language = news_item["news_item_data"]["language"]
                    if language == "":
                        self.language = self.detect_language(content)
                        self.core_api.update_news_item_data(news_item["news_item_data"]["id"], {"language": self.language})
                    else:
                        self.language = language

                current_keywords.update(self.extract_ner(aggregate_content[:self.extraction_text_limit]))
                current_keywords.update(self.generateKeywords(aggregate_content[:self.extraction_text_limit]))
                current_keywords.update(self.lemmatize(current_keywords))

                polyfuzz_matches = self.polyfuzz(all_keywords.keys(), current_keywords.keys())
                current_keywords.update(self.update_keywords_from_polyfuzz(polyfuzz_matches, all_keywords, current_keywords))
                logger.debug(current_keywords)
                self.core_api.update_news_item_tags(aggregate["id"], current_keywords)


        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def extract_ner(self, text: str) -> dict:
        ner_model = self.ner_model
        doc = ner_model(text)
        return {
            ent.text: {"type": ent.label_, "sub_forms": []}
            for ent in doc.ents
            if 16 > len(ent.text) > 2
            and self.not_in_stopwords(ent.text)
        }


    def lemmatize(self, keywords: dict) -> dict:
        for keyword in keywords:
            baseform = self.wordnet_lemmatizer.lemmatize(keyword)
            if baseform != keyword:
                keywords[keyword]["sub_forms"].append(keyword)
                keyword[baseform] = keywords.pop(keyword)
        return keywords

    def convert_list_to_dict(self, keywords: list) -> dict:
        return {keyword["name"]: keyword["sub_forms"] for keyword in keywords}

    def generateKeywords(self, text: str) -> dict:
        keywords = self.keybert_model.extract_keywords(docs=text, keyphrase_ngram_range=(1, 1), use_mmr=True, top_n=10, diversity=0.5, stop_words="english")
        return {keyword: {"type": "CySec", "sub_forms": []} for keyword, distance in keywords if 16 > len(keyword) > 2 and distance > 0.1 and self.not_in_stopwords(keyword)}

    def detect_language(self, text) -> str:
        return py3langid.classify(text)[0]

    def not_in_stopwords(self, keyword: str) -> bool:
        return keyword not in stopwords.words(self.language)



    def polyfuzz(self, from_list: list, to_list: list) -> DataFrame:
        if len(to_list) < 2:
            to_list += to_list
        if not from_list or not to_list:
            return []
        self.polyfuzz_model.match(from_list, to_list)
        df = self.polyfuzz_model.get_matches()
        values = df[df['Similarity'] >=0.65]
        return values.replace(numpy.nan, None)


    def update_keywords_from_polyfuzz(self, polyfuzz_matches: DataFrame, all_keywords: dict, current_keywords: dict) -> dict:
        values_from = polyfuzz_matches['From'] # ["Cyber", "Security"]
        values_to = polyfuzz_matches['To'] # ["Cyber", "Securities"]
        for i, matching_value in enumerate(values_from): # "Cyber", "Security"
            matching_entry = all_keywords[matching_value] # Cyber": { "cybering", "cyberoo", "CYBÄR"}   ## "Security"
            if matching_value in current_keywords: # "Securities"
                current_keywords[matching_value]["sub_forms"] += matching_entry["sub_forms"]  # { "cybering", "cyberk1ller"} += { "cybering", "cyberoo", "CYBÄR"}
                current_keywords[matching_value]["sub_forms"] = list(set(current_keywords[matching_value]["sub_forms"])) # { "cybering", "cyberk1ller", "cyberoo", "CYBÄR"}
            if values_to[i] in current_keywords: # "Securities"
                matching_entry["sub_forms"] += values_to[i]
                current_keywords[values_to[i]] = matching_entry # Security


        return current_keywords # ["Cyber": { "cybering", "cyberk1ller", "cyberoo", "CYBÄR"}, "Security": {"Securities"}, "whatever"]
