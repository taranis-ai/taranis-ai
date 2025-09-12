from pydantic import BaseModel


class PresenterTaskRequest(BaseModel):
    product_id: str
    countdown: int = 0


class PublisherTaskRequest(BaseModel):
    product_id: str
    publisher_id: str


class ConnectorTaskRequest(BaseModel):
    connector_id: str
    story_ids: list[str] | None = None


class CollectorTaskRequest(BaseModel):
    source_id: str
    preview: bool = False
    manual: bool = False


class BotTaskRequest(BaseModel):
    bot_id: str
    filter: dict[str, str] | None = None
