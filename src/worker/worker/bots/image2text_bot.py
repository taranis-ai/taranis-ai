from collections.abc import Callable
from importlib.metadata import entry_points

from models.news_image import MAX_DESCRIPTION_LENGTH
from niquests.exceptions import RequestException

from worker.bot_api import BotServiceUnavailableError
from worker.bots.base_bot import BaseBot


class Image2TextAdapterUnavailable(BotServiceUnavailableError):
    public_message = "The Image2Text service adapter has not been installed."
    reason = "image2text_not_configured"
    retryable = False


def load_image2text_adapter() -> Callable[[bytes, str], str]:
    """An installed adapter owns the external service's wire protocol."""
    adapters = entry_points(group="taranis.image2text", name="describe")
    if len(adapters) != 1:
        raise Image2TextAdapterUnavailable
    return adapters["describe"].load()


class Image2TextBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "IMAGE2TEXT_BOT"
        self.name = "Image2Text"

    def get_filter_dict(self, parameters: dict) -> dict:
        return {**super().get_filter_dict(parameters), "missing_image_description": True}

    def execute(self, parameters: dict | None = None) -> dict:
        adapter = None
        descriptions = {}
        errors = []
        for story in self.get_stories(parameters or {}):
            for item in story.get("news_items", []):
                for image in item.get("images", []):
                    if image.get("description"):
                        continue
                    image_id = image["id"]
                    if adapter is None:
                        adapter = load_image2text_adapter()
                    try:
                        data = self.core_api.get_image(image_id)
                        output = adapter(data, image["mime_type"])
                        caption = output.strip() if isinstance(output, str) else ""
                        if not caption or len(caption) > MAX_DESCRIPTION_LENGTH or "\x00" in caption:
                            raise ValueError("Invalid image description")
                        descriptions[image_id] = caption
                    except (RequestException, ValueError, BotServiceUnavailableError):
                        errors.append(image_id)
        return {
            "message": f"Described {len(descriptions)} images. Failed: {len(errors)}.",
            "changes": {"image_descriptions": descriptions},
            "errors": errors,
        }
