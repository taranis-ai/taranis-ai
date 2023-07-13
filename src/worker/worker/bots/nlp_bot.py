from .base_bot import BaseBot
from worker.log import logger
import datetime
import spacy, spacy.cli
import py3langid
from nltk.stem import WordNetLemmatizer
from polyfuzz import PolyFuzz
from polyfuzz.models import TFIDF
from sentence_transformers import SentenceTransformer
from keybert import KeyBERT
import numpy
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

            all_keywords = []
            for aggregate in data:
                existing_tags = aggregate.get("tags", [])
                aggregate_content = ""

                if len(existing_tags) > 1:
                    all_keywords += existing_tags
                    continue

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

                current_keywords = self.extract_ner(aggregate_content)
                current_keywords += self.generateKeywords(aggregate_content)
                current_keywords = self.lemmatize(current_keywords)
                #logger.debug(f"Polyfuzzing keywords from aggregate: {aggregate['id']}")
                #logger.debug(self.polyfuzz(all_keywords, current_keywords))
                all_keywords += current_keywords
                logger.debug(current_keywords)
                if keywords := list(current_keywords[:20]):
                    self.core_api.update_news_item_tags(aggregate["id"], keywords)


        except Exception:
            logger.log_debug_trace(f"Error running Bot: {self.type}")

    def extract_ner(self, text) -> list:
        ner_model = self.ner_model
        doc = ner_model(text)
        seen = set()
        return [
            {"name": ent.text, "type": ent.label_, "sub_forms": []}
            for ent in doc.ents
            if 16 > len(ent.text) > 2 and ent.text not in seen and not seen.add(ent.text)
        ][:10]

    def lemmatize(self, keywords: dict) -> dict:
        for keyword in keywords:
            baseform = self.wordnet_lemmatizer.lemmatize(keyword["name"])
            if baseform != keyword["name"]:
                keyword["sub_forms"].append(keyword["name"])
                keyword["name"] = baseform
        return keywords


    def polyfuzz(self, existing_keywords: list, keywords: list) -> list:
        from_list = [k["name"] for k in existing_keywords]
        to_list = [k["name"] for k in keywords]
        if not from_list or not to_list:
            return []
        self.polyfuzz_model.match(from_list, to_list)
        df = self.polyfuzz_model.get_matches()
        values = df[df['Similarity'] >=0.65].max()
        values = values.replace(numpy.nan, None)
        return values['From']


    def generateKeywords(self, text):
        keywords = self.keybert_model.extract_keywords(docs=text, keyphrase_ngram_range=(1, 1), use_mmr=True, top_n=10, diversity=0.5, stop_words="english")
        return [{"name": keyword, "type": "CySec", "sub_forms": []} for keyword, distance in keywords if 16 > len(keyword) > 2 and distance > 0.1]

    def detect_language(self, text) -> str:
        return py3langid.classify(text)[0]
