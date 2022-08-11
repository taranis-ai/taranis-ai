from marshmallow import Schema, fields, post_load, EXCLUDE


class TagCloudBaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    word = fields.Str()
    word_quantity = fields.Int()
    collected = fields.DateTime("%d.%m.%Y")


class TagCloudSchema(TagCloudBaseSchema):
    @post_load
    def make_tag_cloud(self, data, **kwargs):
        return TagCloud(**data)


class TagCloud:
    def __init__(self, word, word_quantity, collected):
        self.word = word
        self.word_quantity = word_quantity
        self.collected = collected


class GroupedWordsSchema(TagCloudBaseSchema):
    @post_load
    def make_grouped_words(self, data, **kwargs):
        return GroupedWords(**data)


class GroupedWords:
    def __init__(self, word, word_quantity):
        self.word = word
        self.word_quantity = word_quantity
