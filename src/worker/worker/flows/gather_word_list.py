from prefect import flow, task
import requests
from core.log import logger
from pydantic import BaseModel, Field
from worker.core_api import CoreApi


class WordListTaskRequest(BaseModel):
    """Request model for gather word list task"""
    word_list_id: int = Field(..., description="ID of the word list to gather/update")


@task
def get_word_list_info(word_list_id: int):
    """Get word list information from CoreApi """
    logger.info(f"[gather_word_list] Getting word list info for {word_list_id}")
    
    if not word_list_id:
        logger.error("No word list id provided")
        raise ValueError("No word list id provided")
    
    core_api = CoreApi()
    
    try:
        word_list = core_api.get_word_list(word_list_id)
    except Exception as e:
        logger.error(f"Failed to get word list {word_list_id}: {e}")
        raise RuntimeError(f"Failed to get word list {word_list_id}: {e}") from e
    
    if not word_list:
        logger.error(f"Word list with id {word_list_id} not found")
        raise RuntimeError(f"Word list with id {word_list_id} not found")
    
    return word_list


@task
def download_word_list_content(word_list: dict):
    """Download word list content from URL """
    logger.info(f"[gather_word_list] Downloading content for word list '{word_list['name']}'")
    
    url = word_list["link"]
    logger.info(f"Updating word list {word_list['name']} from {url}")
    
    response = requests.get(url=url, timeout=60)
    
    if not response.ok:
        error_msg = f"Failed to download word list {word_list['name']} - from {url} : {response.status_code}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    content_type = response.headers.get("content-type", "")
    if content_type == "text/csv" or url.endswith(".csv"):
        content_type = "text/csv"
        content = response.text
    elif content_type == "application/json" or url.endswith(".json"):
        content_type = "application/json"
        content = response.json()
    else:
        logger.error("Could not determine content type.")
        raise RuntimeError("Could not determine content type.")
    
    return {
        "word_list_id": word_list["id"],
        "content": content,
        "content_type": content_type
    }


@flow(name="gather-word-list-flow")
def gather_word_list_flow(request: WordListTaskRequest):
    try:
        logger.info(f"[gather_word_list_flow] Starting word list gathering")
        # Get word list info 
        word_list = get_word_list_info(request.word_list_id)
        
        # Download content
        result = download_word_list_content(word_list)
        
        logger.info(f"[gather_word_list_flow] Word list gathering completed successfully")
        
        return result
        
    except Exception as e:
        logger.exception(f"[gather_word_list_flow] Word list gathering failed")
        raise
