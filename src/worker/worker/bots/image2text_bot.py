import time
from io import BytesIO
from itertools import batched
from urllib.parse import quote

from models.news_image import MAX_DESCRIPTION_LENGTH
from niquests import Response, Session
from niquests.exceptions import RequestException
from PIL import Image

from worker.bot_api import BotServiceUnavailableError
from worker.bots.base_bot import BaseBot
from worker.log import logger


BASE_URL = "https://media-intelligence.ait.ac.at"
MODULE = "groundedsam"
BATCH_SIZE = 4
POLL_TIMEOUT = 120


class Image2TextAuthenticationError(BotServiceUnavailableError):
    public_message = "Media Intelligence login failed. Check the Image2Text bot credentials."
    reason = "image2text_authentication_failed"
    retryable = False


def _service_json(response: Response) -> dict:
    response.raise_for_status()
    if response.status_code is None or not 200 <= response.status_code < 300:
        raise ValueError("Unexpected Media Intelligence response status")
    payload = response.json()
    if not isinstance(payload, dict):
        raise TypeError("Invalid Media Intelligence response")
    return payload


def authenticate_media_int(session: Session, parameters: dict) -> None:
    try:
        response = session.post(
            f"{BASE_URL}/login",
            data={"username": parameters["USERNAME"], "password": parameters["PASSWORD"]},
            timeout=(5, 10),
            allow_redirects=False,
        )
        if response.status_code in {401, 403} or _service_json(response).get("authenticated") is not True:
            raise Image2TextAuthenticationError
    except (RequestException, TypeError, ValueError) as exc:
        raise BotServiceUnavailableError from exc


def _upload_file(image_id: str, data: bytes, mime_type: str) -> tuple[str, bytes, str]:
    if mime_type == "image/webp":
        # GroundedSAM silently omits WebP. Bound the size of its decoded PNG upload.
        with Image.open(BytesIO(data), formats=("WEBP",)) as image:
            image.thumbnail((2048, 2048))
            with BytesIO() as png:
                image.save(png, format="PNG")
                return f"{image_id}.png", png.getvalue(), "image/png"
    extension = {"image/png": "png", "image/jpeg": "jpg"}[mime_type]
    return f"{image_id}.{extension}", data, mime_type


def media_int_image_service(session: Session, files: list[tuple[str, bytes, str]]) -> dict[str, str]:
    response = session.post(
        f"{BASE_URL}/modules/{MODULE}/inference",
        data={"image_caption_class": "Tag2Text"},
        files=[("file", file) for file in files],
        timeout=(5, 60),
        allow_redirects=False,
    )
    job_id = _service_json(response).get("job_id")
    if not isinstance(job_id, str) or not job_id:
        raise ValueError("Missing Media Intelligence job ID")
    deadline = time.monotonic() + POLL_TIMEOUT
    while time.monotonic() < deadline:
        job = _service_json(session.get(f"{BASE_URL}/job/get/{quote(job_id, safe='')}", timeout=(5, 10), allow_redirects=False))
        if job.get("status") != "processing":
            break
        time.sleep(0.5)
    else:
        raise TimeoutError("Media Intelligence job timed out")

    records = job["j_metadata"][MODULE]["model_results"][0]["file_records"]
    captions = {}
    for record in records:
        if not isinstance(record, dict) or record.get("status") != "success" or not isinstance(record.get("result"), dict):
            continue
        name = record.get("name")
        caption = record["result"].get("image_caption")
        if isinstance(name, str) and isinstance(caption, str):
            caption = caption.strip()
            if caption and len(caption) <= MAX_DESCRIPTION_LENGTH and "\x00" not in caption:
                captions[name] = caption
    return captions


class Image2TextBot(BaseBot):
    def __init__(self):
        super().__init__()
        self.type = "IMAGE2TEXT_BOT"
        self.name = "Image2Text"

    def get_filter_dict(self, parameters: dict) -> dict:
        return {**super().get_filter_dict(parameters), "missing_image_description": True}

    def _describe_batch(self, session: Session, images: tuple[tuple[str, str], ...]) -> dict[str, str]:
        files = {}
        for image_id, mime_type in images:
            try:
                files[image_id] = _upload_file(image_id, self.core_api.get_image(image_id), mime_type)
            except (RequestException, OSError, ValueError, KeyError) as exc:
                logger.warning(f"Image2Text failed for image {image_id} ({type(exc).__name__})")
        if not files:
            return {}
        try:
            captions = media_int_image_service(session, list(files.values()))
        except (RequestException, TimeoutError, ValueError, KeyError, IndexError, TypeError) as exc:
            logger.warning(f"Image2Text inference failed for {len(files)} images ({type(exc).__name__})")
            return {}
        return {image_id: captions[name] for image_id, (name, _, _) in files.items() if name in captions}

    def execute(self, parameters: dict | None = None) -> dict:
        parameters = parameters or {}
        descriptions = parameters.get("_llm_batch_state", {}).setdefault("image_descriptions", {})
        save_state = parameters.get("_save_llm_batch_state")
        pending = {
            image["id"]: image["mime_type"]
            for story in self.get_stories(parameters)
            for item in story.get("news_items", [])
            for image in item.get("images", [])
            if not image.get("description") and image["id"] not in descriptions
        }
        if pending:
            # This service needs its login cookie across requests, isolated from Core and other bots.
            with Session(retries=0, disable_http3=True) as session:
                authenticate_media_int(session, parameters)
                for batch in batched(pending.items(), BATCH_SIZE):
                    if captions := self._describe_batch(session, batch):
                        descriptions.update(captions)
                        if save_state:
                            save_state()
        errors = [image_id for image_id in pending if image_id not in descriptions]
        return {
            "message": f"Described {len(descriptions)} images. Failed: {len(errors)}.",
            "changes": {"image_descriptions": descriptions},
            "errors": errors,
        }
