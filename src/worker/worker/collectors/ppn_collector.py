import json
import os
from pathlib import Path

from models.assess import NewsItem

from worker.collectors.base_web_collector import BaseCollector
from worker.log import logger


class PPNCollector(BaseCollector):
    def __init__(self):
        super().__init__()
        self.type = "PPN_COLLECTOR"
        self.name = "ppn Collector"
        self.description = "Collector for gathering news from the ppn dataset: https://github.com/hybrinfox/ppn"
        self.osint_source_id: str

        self.news_items = []
        self.path: Path
        self.last_attempted = None

    def parse_source(self, source):
        self.path = Path(source["parameters"].get("PATH", None))
        self.osint_source_id = str(source["id"])
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
        items = self.load_from_folder(self.path)
        self.news_items = self.create_news_items(items)
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
                date = item.get("date_publish", "") or item.get("date_download", "")

                news_items.append(
                    NewsItem(
                        osint_source_id=self.osint_source_id,
                        author=",".join(item.get("author", [])),
                        title=item.get("title", ""),
                        content=content,
                        link=item.get("url", ""),
                        source=item.get("source_domain", ""),
                        published=date,
                        language=item.get("language", ""),
                    )
                )
        return news_items

    def load_from_folder(self, path: Path, languages: list[str] | None = None) -> list[dict]:
        if languages is None:
            languages = ["ar", "de", "en", "es", "fr", "it", "ua", "ru", "zh"]
        docs = []

        dataset_files = os.listdir(path)
        for file in dataset_files:
            if file[-4:] == "json":
                with open(path / file, "r") as f:
                    lines = f.readlines()[0]
                doc_json = json.loads(lines)
                if doc_json["language"] in languages:
                    docs.append(doc_json)
        return docs
