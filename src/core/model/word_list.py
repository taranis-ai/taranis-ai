import sqlalchemy
from marshmallow import post_load, fields
from sqlalchemy import orm, func, or_, and_
from sqlalchemy.sql.expression import cast

from managers.db_manager import db
from model.acl_entry import ACLEntry
from taranisng.schema.acl_entry import ItemType
from taranisng.schema.word_list import WordListCategorySchema, WordListEntrySchema, WordListSchema, \
    WordListPresentationSchema


class NewWordListEntrySchema(WordListEntrySchema):

    @post_load
    def make(self, data, **kwargs):
        return WordListEntry(**data)


class NewWordListCategorySchema(WordListCategorySchema):
    entries = fields.Nested(NewWordListEntrySchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return WordListCategory(**data)


class NewWordListSchema(WordListSchema):
    categories = fields.Nested(NewWordListCategorySchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return WordList(**data)


class WordList(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())
    use_for_stop_words = db.Column(db.Boolean, default=False)

    categories = db.relationship("WordListCategory", cascade="all, delete-orphan")

    def __init__(self, id, name, description, categories, use_for_stop_words):
        self.id = None
        self.name = name
        self.description = description
        self.categories = categories
        self.use_for_stop_words = use_for_stop_words
        self.title = ""
        self.subtitle = ""
        self.tag = ""

    @orm.reconstructor
    def reconstruct(self):
        self.title = self.name
        self.subtitle = self.description
        self.tag = "mdi-format-list-bulleted-square"

        self.categories.sort(key=WordListCategory.sort)

    @classmethod
    def find(cls, id):
        return cls.query.get(id)

    @classmethod
    def allowed_with_acl(cls, word_list_id, user, see, access, modify):

        query = db.session.query(WordList.id).distinct().group_by(WordList.id).filter(
            WordList.id == word_list_id)

        query = query.outerjoin(ACLEntry, and_(cast(WordList.id, sqlalchemy.String) == ACLEntry.item_id,
                                               ACLEntry.item_type == ItemType.WORD_LIST))

        query = ACLEntry.apply_query(query, user, see, access, modify)

        return query.scalar() is not None

    @classmethod
    def get_all(cls):
        return cls.query.order_by(db.asc(WordList.name)).all()

    @classmethod
    def get(cls, search, user, acl_check):
        query = cls.query.distinct().group_by(WordList.id)

        if acl_check is True:
            query = query.outerjoin(ACLEntry, and_(cast(WordList.id, sqlalchemy.String) == ACLEntry.item_id,
                                                   ACLEntry.item_type == ItemType.WORD_LIST))
            query = ACLEntry.apply_query(query, user, True, False, False)

        if search is not None:
            search_string = '%' + search.lower() + '%'
            query = query.filter(or_(
                func.lower(WordList.name).like(search_string),
                func.lower(WordList.description).like(search_string)))

        return query.order_by(db.asc(WordList.name)).all(), query.count()

    @classmethod
    def get_all_json(cls, search, user, acl_check):
        word_lists, count = cls.get(search, user, acl_check)
        schema = WordListPresentationSchema(many=True)
        return {'total_count': count, 'items': schema.dump(word_lists)}

    @classmethod
    def add_new(cls, data):
        schema = NewWordListSchema()
        word_list = schema.load(data)
        db.session.add(word_list)
        db.session.commit()

    @classmethod
    def update(cls, word_list_id, data):
        schema = NewWordListSchema()
        updated_word_list = schema.load(data)
        word_list = cls.query.get(word_list_id)
        word_list.name = updated_word_list.name
        word_list.description = updated_word_list.description
        word_list.use_for_stop_words = updated_word_list.use_for_stop_words
        word_list.categories = updated_word_list.categories
        db.session.commit()

    @classmethod
    def delete(cls, id):
        word_list = cls.query.get(id)
        db.session.delete(word_list)
        db.session.commit()

    @classmethod
    def add_word_list_category(cls, id, category):
        word_list = cls.find(id)

        category_schema = NewWordListCategorySchema()
        category = category_schema.load(category)

        word_list.categories.append(category)
        db.session.commit()


class WordListCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    word_list_id = db.Column(db.Integer, db.ForeignKey('word_list.id'))

    entries = db.relationship("WordListEntry", cascade="all, delete-orphan")

    def __init__(self, name, description, entries):
        self.id = None
        self.name = name
        self.description = description
        self.entries = entries

    @staticmethod
    def sort(category):
        return category.name

    @classmethod
    def find(cls, id, name):
        return cls.query.filter_by(word_list_id=id).filter_by(name=name).scalar()

    @classmethod
    def get_categories(cls, id):
        categories = cls.query.filter_by(word_list_id=id).all()
        word_list_categories_schema = NewWordListCategorySchema(many=True)
        return word_list_categories_schema.dump(categories)


class WordListEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(), nullable=False)
    description = db.Column(db.String())

    word_list_category_id = db.Column(db.Integer, db.ForeignKey('word_list_category.id'))

    def __init__(self, value, description):
        self.id = None
        self.value = value
        self.description = description

    @classmethod
    def identical(cls, value, word_list_category_id):
        return db.session.query(db.exists().where(WordListEntry.value == value).
                                where(WordListEntry.word_list_category_id == word_list_category_id)).scalar()

    @classmethod
    def delete_entries(cls, id, name):
        word_list_category = WordListCategory.find(id, name)
        cls.query.filter_by(word_list_category_id=word_list_category.id).delete()
        db.session.commit()

    @classmethod
    def update_word_list_entries(cls, id, name, entries):
        word_list_category = WordListCategory.find(id, name)

        entries_schema = NewWordListEntrySchema(many=True)
        entries = entries_schema.load(entries)

        for entry in entries:
            if not WordListEntry.identical(entry.value, word_list_category.id):
                word_list_category.entries.append(entry)
                db.session.commit()

    @classmethod
    def stopwords_subquery(cls):
        return db.session.query(func.lower(WordListEntry.value)).distinct().group_by(WordListEntry.value).join(
            WordListCategory,
            WordListCategory.id == WordListEntry.word_list_category_id).join(
            WordList, WordList.id == WordListCategory.word_list_id).filter(
            WordList.use_for_stop_words == True).subquery()

