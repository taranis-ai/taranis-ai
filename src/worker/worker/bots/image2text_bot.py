from collections.abc import Callable
from importlib.metadata import entry_points

from models.news_image import MAX_DESCRIPTION_LENGTH
from niquests.exceptions import RequestException

from worker.bot_api import BotServiceUnavailableError
from worker.bots.base_bot import BaseBot
from worker.log import logger


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
        parameters = parameters or {}
        descriptions = parameters.get("_llm_batch_state", {}).setdefault("image_descriptions", {})
        save_state = parameters.get("_save_llm_batch_state")
        errors = []
        for story in self.get_stories(parameters):
            for item in story.get("news_items", []):
                for image in item.get("images", []):
                    image_id = image["id"]
                    if image.get("description") or image_id in descriptions:
                        continue
                    if adapter is None:
                        adapter = load_image2text_adapter()
                    try:
                        data = self.core_api.get_image(image_id)
                        output = adapter(data, image["mime_type"])
                        caption = output.strip() if isinstance(output, str) else ""
                        if not caption or len(caption) > MAX_DESCRIPTION_LENGTH or "\x00" in caption:
                            raise ValueError("Invalid image description")
                    except (RequestException, ValueError, BotServiceUnavailableError) as exc:
                        logger.warning(f"Image2Text failed for image {image_id} ({type(exc).__name__})")
                        logger.exception()
                        errors.append(image_id)
                        continue
                    descriptions[image_id] = caption
                    if save_state:
                        save_state()
        return {
            "message": f"Described {len(descriptions)} images. Failed: {len(errors)}.",
            "changes": {"image_descriptions": descriptions},
            "errors": errors,
        }
