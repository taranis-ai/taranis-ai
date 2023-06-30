import datetime
import re
from typing import Any
from sqlalchemy import func
from sqlalchemy.sql import label

from core.managers.db_manager import db
from core.model.base_model import BaseModel


class TagCloud(BaseModel):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String())
    word_quantity = db.Column(db.BigInteger)
    collected = db.Column(db.Date)

    def __init__(self, word, word_quantity, collected):
        self.id = None
        self.word = word
        self.word_quantity = word_quantity
        self.collected = collected

    @classmethod
    def add_tag_clouds(cls, tag_clouds):
        for tag_cloud in tag_clouds:
            word = TagCloud.query.filter_by(word=tag_cloud.word, collected=tag_cloud.collected).first()
            if word is not None:
                word.word_quantity += 1
            else:
                db.session.add(tag_cloud)
        db.session.commit()

    @classmethod
    def get_grouped_words(cls, tag_cloud_day):
        day_filter = (datetime.datetime.now() - datetime.timedelta(days=tag_cloud_day)).date()
        grouped_words = (
            db.session.query(TagCloud.word, label("word_quantity", func.sum(TagCloud.word_quantity)))
            .filter(TagCloud.collected == day_filter)
            .group_by(TagCloud.word)
            .order_by(db.desc("word_quantity"))
            .limit(100)
            .all()
        )
        return [grouped_word.to_dict() for grouped_word in grouped_words]

    @classmethod
    def delete_words(cls):
        limit_days = 7
        limit = (datetime.datetime.now() - datetime.timedelta(days=limit_days)).date()
        cls.query.filter(cls.collected < limit).delete()
        db.session.commit()

    @staticmethod
    def unwanted_chars(news_item_data):
        title = news_item_data.title.lower()
        title = re.sub(r"[^a-zA-Z0-9 ]", r"", title)
        review = news_item_data.review.lower()
        review = re.sub(r"[^a-zA-Z0-9 ]", r"", review)
        content = news_item_data.content.lower()
        content = re.sub(r"[^a-zA-Z0-9 ]", r"", content)
        return title, review, content

    @staticmethod
    def create_tag_cloud(word):
        collected = datetime.datetime.now().date()
        return TagCloud(word, 1, collected)

    @staticmethod
    def news_item_words(title, review, content):
        news_item_title_words = title.split()
        news_item_review_words = review.split()
        news_item_content_words = content.split()
        return news_item_title_words, news_item_review_words, news_item_content_words

    @staticmethod
    def news_items_words(
        title,
        review,
        content,
        news_items_title_words,
        news_items_review_words,
        news_items_content_words,
    ):
        (
            news_item_title_words,
            news_item_review_words,
            news_item_content_words,
        ) = TagCloud.news_item_words(title, review, content)
        news_items_title_words.extend(news_item_title_words)
        news_items_review_words.extend(news_item_review_words)
        news_items_content_words.extend(news_item_content_words)
        return news_items_title_words, news_items_review_words, news_items_content_words

    @classmethod
    def generate_tag_cloud_words(cls, news_item_data):
        news_items_title_words = []
        news_items_review_words = []
        news_items_content_words = []
        title, review, content = TagCloud.unwanted_chars(news_item_data)

        (
            news_items_title_words,
            news_items_review_words,
            news_items_content_words,
        ) = TagCloud.news_items_words(
            title,
            review,
            content,
            news_items_title_words,
            news_items_review_words,
            news_items_content_words,
        )
        news_items_words = news_items_title_words + news_items_review_words + news_items_content_words

        tag_cloud_words = [TagCloud.create_tag_cloud(word_item) for word_item in set(news_items_words)]
        cls.add_tag_clouds(tag_cloud_words)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        return data
