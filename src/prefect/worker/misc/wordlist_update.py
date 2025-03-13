import requests

from worker.log import logger
from worker.core_api import CoreApi


def update_wordlist(word_list_id: int):
    core_api = CoreApi()

    if not word_list_id:
        logger.error("No word list id provided")
        return {"error": "No word list id provided"}

    try:
        word_list = core_api.get_word_list(word_list_id)
    except Exception as e:
        logger.error(f"Failed to get word list {word_list_id}: {e}")
        return {"error": f"Failed to get word list {word_list_id}: {e}"}

    if not word_list:
        logger.error(f"Word list with id {word_list_id} not found")
        return {"error": f"Word list with id {word_list_id} not found"}

    url = word_list["link"]
    logger.info(f"Updating word list {word_list['name']} from {url}")
    response = requests.get(url=url, timeout=60)
    if not response.ok:
        logger.error(f"Failed to download word list {word_list['name']} - from {url} : {response.status_code}")
        return {"error": f"Failed to download word list {word_list['name']} - from {url} : {response.status_code}"}

    content_type = response.headers.get("content-type", "")
    if content_type == "text/csv" or url.endswith(".csv"):
        content_type = "text/csv"
        content = response.text
    elif content_type == "application/json" or url.endswith(".json"):
        content_type = "application/json"
        content = response.json()
    else:
        logger.error("Could not determine content type.")
        return {"error": "Could not determine content type."}

    return {"word_list_id": word_list["id"], "content": content, "content_type": content_type}
