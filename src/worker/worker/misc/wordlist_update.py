import niquests as requests

from worker.core_api import CoreApi
from worker.log import logger


def update_wordlist(word_list_id: str):
    core_api = CoreApi()

    if not word_list_id:
        logger.error("No word list id provided")
        raise ValueError("No word list id provided")

    try:
        word_list = core_api.get_word_list(word_list_id)
    except Exception as e:
        logger.error(f"Failed to get word list {word_list_id}: {e}")
        raise RuntimeError(f"Failed to get word list {word_list_id}: {e}") from e

    if not word_list:
        logger.error(f"Word list with id {word_list_id} not found")
        raise LookupError(f"Word list with id {word_list_id} not found")

    word_list_name = word_list.get("name", f"word_list_{word_list_id}")
    url = word_list["link"]
    logger.info(f"Updating word list {word_list_name} ({word_list_id}) from {url}")
    response = requests.get(url=url, timeout=60)
    if not response.ok:
        logger.error(f"Failed to download word list {word_list_name} ({word_list_id}) from {url}: {response.status_code}")
        raise RuntimeError(f"Failed to download word list {word_list_name} ({word_list_id}) from {url}: {response.status_code}")

    content_type = response.headers.get("content-type", "")
    content: str | dict | list
    if content_type == "text/csv" or url.endswith(".csv"):
        content_type = "text/csv"
        text_content = response.text
        if text_content is None:
            raise ValueError("Downloaded CSV word list is empty")
        content = text_content
    elif content_type == "application/json" or url.endswith(".json"):
        content_type = "application/json"
        json_content = response.json()
        if not isinstance(json_content, (str, dict, list)):
            raise ValueError("Downloaded JSON word list must be a JSON object, list, or string")
        content = json_content
    else:
        logger.error("Could not determine content type.")
        raise ValueError("Could not determine content type.")

    # Save the downloaded content to the database via Core API
    try:
        result = core_api.update_word_list(word_list_id, content, content_type)
        if not result:
            logger.error(f"Failed to save word list {word_list_name} ({word_list_id}): core API returned an empty response")
            raise RuntimeError("core API returned an empty response")
        logger.info(
            f"Successfully updated word list {word_list_name} ({word_list_id}) with "
            f"{len(content) if isinstance(content, (list, str)) else 'unknown'} entries"
        )
        return {
            "word_list_id": word_list_id,
            "content": content,
            "content_type": content_type,
            "message": "Successfully updated wordlist",
        }
    except Exception as e:
        logger.error(f"Failed to save word list {word_list_name} ({word_list_id}): {e}")
        raise RuntimeError(f"Failed to save word list {word_list_name} ({word_list_id}): {e}") from e
