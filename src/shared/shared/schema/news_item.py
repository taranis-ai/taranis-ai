from marshmallow import Schema, fields, post_load, EXCLUDE

from shared.schema.acl_entry import ACLEntryStatusSchema


class NewsItemAttributeBaseSchema(Schema):
    id = fields.Int()
    key = fields.Str()
    value = fields.Str()
    binary_mime_type = fields.Str()


class NewsItemAttributeSchema(NewsItemAttributeBaseSchema):
    binary_value = fields.Str()


class NewsItemAttribute:
    def __init__(self, key, value, binary_mime_type, binary_value):
        # self.id = id
        self.key = key
        self.value = value
        self.binary_mime_type = binary_mime_type
        self.binary_value = binary_value


class NewsItemDataBaseSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Str(load_default=None)
    hash = fields.Str()
    title = fields.Str()
    review = fields.Str()
    source = fields.Str()
    link = fields.Str()
    published = fields.DateTime()
    author = fields.Str()
    collected = fields.DateTime()
    osint_source_id = fields.Str(load_default=None)


class NewsItemDataSchema(NewsItemDataBaseSchema):
    content = fields.Str()
    attributes = fields.Nested(NewsItemAttributeSchema, many=True)

    @post_load
    def make(self, data, **kwargs):
        return NewsItemData(**data)


class NewsItemRemoteSchema(Schema):
    hash = fields.Str()
    title = fields.Str()
    review = fields.Str()
    source = fields.Str()
    link = fields.Str()
    published = fields.DateTime()
    author = fields.Str()
    collected = fields.DateTime()
    content = fields.Str()
    attributes = fields.Nested(NewsItemAttributeSchema, many=True)
    relevance = fields.Int()


class NewsItemDataPresentationSchema(NewsItemDataBaseSchema):
    remote_source = fields.Str()
    content = fields.Str()
    attributes = fields.Nested(NewsItemAttributeBaseSchema, many=True)


class NewsItemData:
    def __init__(
        self,
        id,
        hash,
        title,
        review,
        source,
        link,
        published,
        author,
        collected,
        content,
        osint_source_id,
        attributes,
    ):
        self.id = id
        self.hash = hash
        self.title = title
        self.review = review
        self.source = source
        self.link = link
        self.published = published
        self.author = author
        self.collected = collected
        self.content = content
        self.osint_source_id = osint_source_id
        self.attributes = attributes


class NewsItemBaseSchema(Schema):
    id = fields.Int()
    likes = fields.Int()
    dislikes = fields.Int()
    read = fields.Bool()
    important = fields.Bool()
    me_like = fields.Bool()
    me_dislike = fields.Bool()
    news_item_data = fields.Nested(NewsItemDataSchema)


class NewsItemTag:
    def __init__(self, name, tag_type):
        self.name = name
        self.tag_type = tag_type


class NewsItemTagSchema(Schema):
    name = fields.Str()
    tag_type = fields.Str()


class NewsItemPresentationSchema(NewsItemBaseSchema, ACLEntryStatusSchema):
    pass


class NewsItemSchema(NewsItemBaseSchema):
    news_item_data = fields.Nested(NewsItemDataPresentationSchema)


class NewsItemAggregateSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    created = fields.DateTime()
    comments = fields.Str()
    likes = fields.Int()
    dislikes = fields.Int()
    read = fields.Bool()
    important = fields.Bool()
    me_like = fields.Bool()
    me_dislike = fields.Bool()
    in_reports_count = fields.Int()
    tags = fields.Nested(NewsItemTagSchema, many=True)
    summary = fields.String()
    news_items = fields.Nested(NewsItemPresentationSchema, many=True)


class NewsItemAggregateIdSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    id = fields.Int()

    @post_load
    def make(self, data, **kwargs):
        return NewsItemAggregateId(**data)


class NewsItemAggregateId:
    def __init__(self, id):
        self.id = id
