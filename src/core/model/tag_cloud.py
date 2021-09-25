import re
from managers.db_manager import db
from marshmallow import post_load
from taranisng.schema.tag_cloud import TagCloudSchema, GroupedWordsSchema
from sqlalchemy import func
from sqlalchemy.sql import label
import datetime
from model.osint_source import OSINTSource


class NewTagCloudSchema(TagCloudSchema):

    @post_load
    def make_tag_cloud(self, data, **kwargs):
        return TagCloud(**data)


class TagCloud(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String())
    word_quantity = db.Column(db.BigInteger)
    collected = db.Column(db.Date)

    def __init__(self, word, word_quantity, collected):
        self.word = word
        self.word_quantity = word_quantity
        self.collected = collected

    @classmethod
    def identical(cls, word, collected):
        return db.session.query(db.exists().where(TagCloud.word == word).where(TagCloud.collected == collected)). \
            scalar()

    @classmethod
    def add_tag_clouds(cls, tag_clouds):
        for tag_cloud in tag_clouds:
            if TagCloud.identical(tag_cloud.word, tag_cloud.collected):
                word = TagCloud.query.filter_by(word=tag_cloud.word).first()
                word.word_quantity += 1
            else:
                db.session.add(tag_cloud)
        db.session.commit()

    @classmethod
    def get_grouped_words(cls):
        grouped_words = db.session.query(TagCloud.word, label('word_quantity', func.sum(TagCloud.word_quantity))). \
            group_by(TagCloud.word).order_by(db.desc('word_quantity')).limit(100).all()
        grouped_words_schema = GroupedWordsSchema(many=True)
        return grouped_words_schema.dump(grouped_words)

    @classmethod
    def delete_words(cls):
        limit_days = 7
        limit = datetime.datetime.now() - datetime.timedelta(days=limit_days)
        cls.query.filter(cls.collected < limit).delete()
        db.session.commit()

    @staticmethod
    def unwanted_chars(news_item_data):
        title = news_item_data.title.lower()
        title = re.sub(r'[^a-zA-Z0-9 ]', r'', title)
        review = news_item_data.review.lower()
        review = re.sub(r'[^a-zA-Z0-9 ]', r'', review)
        content = news_item_data.content.lower()
        content = re.sub(r'[^a-zA-Z0-9 ]', r'', content)
        return title, review, content

    @staticmethod
    def counting_words(word, words_counts):
        words_counts[word] = 1

    @staticmethod
    def create_tag_cloud(i, tag_cloud_words):
        word = i[0]
        word_quantity = i[1]
        collected = datetime.datetime.now().date()
        tag_cloud_word = TagCloud(word, word_quantity, collected)
        return tag_cloud_words.append(tag_cloud_word)

    @staticmethod
    def news_item_words(title, review, content):
        news_item_title_words = title.split()
        news_item_review_words = review.split()
        news_item_content_words = content.split()
        return news_item_title_words, news_item_review_words, news_item_content_words

    @staticmethod
    def news_items_words(title, review, content, news_items_title_words, news_items_review_words,
                         news_items_content_words):
        news_item_title_words, news_item_review_words, news_item_content_words = TagCloud.news_item_words(title, review,
                                                                                                          content)
        news_items_title_words.extend(news_item_title_words)
        news_items_review_words.extend(news_item_review_words)
        news_items_content_words.extend(news_item_content_words)
        return news_items_title_words, news_items_review_words, news_items_content_words

    @classmethod
    def generate_tag_cloud_words(cls, news_item_data):

        news_items_title_words = []
        news_items_review_words = []
        news_items_content_words = []
        tag_cloud_words = []
        words_counts = dict()

        source = OSINTSource.query.get(news_item_data.osint_source_id)

        if source:

            one_use_stop_word_list = set()

            for word_list in source.word_lists:
                if word_list.use_for_stop_words is True:
                    for category in word_list.categories:
                        for entry in category.entries:
                            one_use_stop_word_list.add(entry.value.lower())

            if one_use_stop_word_list:

                title, review, content = TagCloud.unwanted_chars(news_item_data)

                news_item_title_words = [word for word in title.split() if word not in
                                         one_use_stop_word_list]
                news_items_title_words.extend(news_item_title_words)
                news_item_review_words = [word for word in review.split() if word not in
                                          one_use_stop_word_list]
                news_items_review_words.extend(news_item_review_words)
                news_item_content_words = [word for word in content.split() if word not in
                                           one_use_stop_word_list]
                news_items_content_words.extend(news_item_content_words)
                news_items_words = news_items_title_words + news_items_review_words + news_items_content_words

                news_items_words = set(news_items_words)

                for word in news_items_words:
                    TagCloud.counting_words(word, words_counts)

                for i in words_counts.items():
                    TagCloud.create_tag_cloud(i, tag_cloud_words)

                cls.add_tag_clouds(tag_cloud_words)

            else:

                title, review, content = TagCloud.unwanted_chars(news_item_data)

                news_items_title_words, news_items_review_words, news_items_content_words = TagCloud. \
                    news_items_words(title, review, content, news_items_title_words, news_items_review_words,
                                     news_items_content_words)
                news_items_words = news_items_title_words + news_items_review_words + news_items_content_words

                news_items_words = set(news_items_words)

                for word in news_items_words:
                    TagCloud.counting_words(word, words_counts)

                for i in words_counts.items():
                    TagCloud.create_tag_cloud(i, tag_cloud_words)

                cls.add_tag_clouds(tag_cloud_words)

        else:

            title, review, content = TagCloud.unwanted_chars(news_item_data)

            news_items_title_words, news_items_review_words, news_items_content_words = TagCloud. \
                news_items_words(title, review, content, news_items_title_words, news_items_review_words,
                                 news_items_content_words)
            news_items_words = news_items_title_words + news_items_review_words + news_items_content_words

            news_items_words = set(news_items_words)

            for word in news_items_words:
                TagCloud.counting_words(word, words_counts)

            cls.add_tag_clouds(tag_cloud_words)
