from marshmallow import Schema, fields, EXCLUDE, post_load

from shared.schema.presentation import PresentationSchema


class WordListEntrySchema(Schema):
    value = fields.Str()
    description = fields.Str()

    @post_load
    def make(self, data, **kwargs):
        return WordListEntry(**data)


class WordListSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    use_for_stop_words = fields.Bool()
    link = fields.Str(allow_none=True)
    entries = fields.Nested(WordListEntrySchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return WordList(**data)


class WordListPresentationSchema(WordListSchema, PresentationSchema):
    pass


class WordList:
    def __init__(self, id, name, description, use_for_stop_words, link, entries):
        self.id = id
        self.name = name
        self.description = description
        self.use_for_stop_words = use_for_stop_words
        self.link = link
        self.entries = entries


class WordListEntry:
    def __init__(self, value="", description=""):
        self.value = value
        self.description = description
