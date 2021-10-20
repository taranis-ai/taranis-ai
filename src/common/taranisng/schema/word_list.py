from marshmallow import Schema, fields, EXCLUDE, post_load
from taranisng.schema.presentation import PresentationSchema


class WordListEntrySchema(Schema):
    value = fields.Str()
    description = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        return WordListEntry(**data)


class WordListCategorySchema(Schema):
    name = fields.Str()
    description = fields.Str()
    entries = fields.Nested(WordListEntrySchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return WordListCategory(**data)


class WordListSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    use_for_stop_words = fields.Bool()
    categories = fields.Nested(WordListCategorySchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return WordList(**data)


class WordListPresentationSchema(WordListSchema, PresentationSchema):
    pass


class WordList:

    def __init__(self, id, name, description, use_for_stop_words, categories):
        self.id = id
        self.name = name
        self.description = description
        self.use_for_stop_words = use_for_stop_words
        self.categories = categories


class WordListCategory:

    def __init__(self, name, description, entries):
        self.name = name
        self.description = description
        self.entries = entries


class WordListEntry:

    def __init__(self, value = '', description = ''):
        self.value = value
        self.description = description


class WordListIdSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()

    @post_load
    def make(self, data, **kwargs):
        return WordListId(**data)


class WordListId:

    def __init__(self, id):
        self.id = id
