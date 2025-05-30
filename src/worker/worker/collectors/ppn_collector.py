import json
import os
import pickle
from pathlib import Path
from worker.log import logger
from worker.types import NewsItem
from worker.collectors.base_web_collector import BaseCollector


class PPNCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.type = "PPN_COLLECTOR"
        self.name = "ppn Collector"
        self.description = "Collector for gathering news from the ppn dataset: https://github.com/hybrinfox/ppn"
        self.osint_source_id: str

        self.news_items = []
        self.path: str
        self.last_attempted = None

    def parse_source(self, source):
        self.path = source["parameters"].get("PATH", None)
        self.osint_source_id = source["id"]
        if not self.path:
            logger.error("No PATH set")
            raise ValueError("No PATH set")

    def collect(self, source, manual: bool = False):
        self.parse_source(source)
        logger.info(f"Collecting ppn dataset from {self.path}")

        try:
            return self.ppn_collector(source)
        except Exception as e:
            logger.exception(f"PPN Collector failed to collect ppn dataset from {self.path} with error: {str(e)}")
            return str(e)

    def ppn_collector(self, source):
        # load news
        ppn_items = self.load_ppn()
        self.news_items = self.create_news_items(ppn_items)
        news_item_batches = self.batch_news_items()
        for batch in news_item_batches:
            self.publish(batch, source)
        return None

    def batch_news_items(self, batch_size: int = 400) -> list[list[NewsItem]]:
        batches = []
        batches.extend(self.news_items[i : i + batch_size] for i in range(0, len(self.news_items), batch_size))
        return batches

    def create_news_items(self, ppn_items: list[dict]) -> list[NewsItem]:
        news_items = []

        for item in ppn_items:
            if content := item.get("maintext", None):
                news_items.append(
                    NewsItem(
                        osint_source_id=self.osint_source_id,
                        author=",".join(item.get("author", [])),
                        title=item.get("title", ""),
                        content=content,
                        web_url=item.get("url", ""),
                        source=item.get("source_domain", ""),
                        published_date=item.get("date_publish", ""),
                        language=item.get("language", ""),
                    )
                )
        return news_items

    def load_from_folder(self, path: str, languages: list[str] | None = None) -> list[dict]:
        if languages is None:
            languages = ["ar", "de", "en", "es", "fr", "it", "ua", "ru", "zh"]
        docs = []

        dataset_path = self.path / Path(path)

        dataset_files = os.listdir(dataset_path)
        for file in dataset_files:
            if file[-4:] == "json":
                with open(dataset_path / file, "r") as f:
                    lines = f.readlines()[0]
                doc_json = json.loads(lines)
                if doc_json["language"] in languages:
                    docs.append(doc_json)
        return docs

    def load_from_folder_tribunal_ukraine(self, path: str, languages: list[str] | None = None) -> list[dict]:
        if languages is None:
            languages = ["de", "en", "es", "fr", "ru"]
        docs = []

        dataset_path = self.path / Path(path)

        language_list_tribunal_ukraine = [f"lang={lang}" for lang in languages]
        if "de" in languages:
            language_list_tribunal_ukraine.append("lang=_")
        dataset_files = os.listdir(dataset_path)
        for file in dataset_files:
            if file[-4:] == "json":
                for lang in language_list_tribunal_ukraine:
                    if lang in file:
                        with open(dataset_path / file, "r") as f:
                            lines = f.readlines()[0]
                        doc_json = json.loads(lines)
                        docs.append(doc_json)
        return docs

    def load_rrn(self):
        return self.load_from_folder("ppn_data/2023/09/13/rrn.media/", languages=["ar", "de", "en", "es", "fr", "it", "ua", "ru", "zh"])

    def load_tribunalukraine(self):
        return self.load_from_folder_tribunal_ukraine("ppn_data/2023/11/09/tribunalukraine.info/", languages=["de", "en", "es", "fr", "ru"])

    def load_waronfakes(self):
        return self.load_from_folder("ppn_data/2023/11/09/waronfakes.com/", languages=["ar", "de", "en", "es", "fr", "zh"])

    def load_lavirgule(self):
        return self.load_from_folder("ppn_data/2023/11/09/lavirgule.news/", languages=["ar", "de", "en", "es", "fr", "it", "ua", "ru", "zh"])

    def load_notrepays(self):
        return self.load_from_folder("ppn_data/2023/11/09/notrepays.today/", languages=["ar", "de", "en", "es", "fr", "it", "ua", "ru", "zh"])

    def load_regular_fr(self):
        return pickle.load(open(str(Path(self.path) / "regular_data/regular_ukraine_FR.pkl"), "rb"))

    def load_regular_en(self):
        return pickle.load(open(str(Path(self.path) / "regular_data/regular_ukraine_EN.pkl"), "rb"))

    def load_ppn(self):
        rrn_docs = self.load_rrn()
        tribunalukraine_docs = self.load_tribunalukraine()
        waron_fakes_doc = self.load_waronfakes()
        docs = rrn_docs + tribunalukraine_docs + waron_fakes_doc
        lavirgule_docs = self.load_lavirgule()
        notrepays_docs = self.load_notrepays()
        docs = docs + lavirgule_docs + notrepays_docs
        return docs

    def load_regular(self):
        return self.load_regular_fr() + self.load_regular_en()
