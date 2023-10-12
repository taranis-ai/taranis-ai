import requests

from worker.log import logger
from worker.core_api import CoreApi


def update_wordlist(word_list_id: int):
    core_api = CoreApi()

    if not word_list_id:
        logger.error("No word list id provided")
        return "No word list id provided"

    word_list = core_api.get_word_list(word_list_id)

    if not word_list:
        logger.error(f"Word list with id {word_list_id} not found")
        return f"Word list with id {word_list_id} not found"

    url = word_list["link"]
    logger.info(f"Updating word list {word_list['name']} from {url}")
    response = requests.get(url=url)
    if not response.ok:
        logger.error(f"Failed to download word list {word_list['name']} - from {url} : {response.status_code}")
        return

    content_type = response.headers.get("content-type", "")
    if content_type == "text/csv" or url.endswith(".csv"):
        content_type = "text/csv"
        content = response.text
    elif content_type == "application/json" or url.endswith(".json"):
        content_type = "application/json"
        content = response.json()
    else:
        logger.error("Could not determine content type.")
        return

    logger.debug(f"Updating word list {word_list['name']} with {len(content)} entries - {content_type}")

    response = core_api.update_word_list(word_list["id"], content, content_type)

    if not response:
        logger.error(f"Failed to update word list {word_list['name']}")
        return

    logger.info(response)
    return response
