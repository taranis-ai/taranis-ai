from celery import shared_task

from worker.log import logger
from worker.core_api import CoreApi
from worker.bots import bot_tasks
from worker.collectors import collector_tasks


@shared_task(time_limit=60)
def collect(source_id: str):
    if err := collector_tasks.collect_by_source_id(source_id):
        return err
    execute_post_collection_bots.delay({"SOURCE": source_id})  # type: ignore
    return f"Succesfully collected source {source_id}"


@shared_task(time_limit=180)
def execute_bot(bot_id: str, filter: dict | None = None):
    return bot_tasks.execute_by_id(bot_id, filter)


@shared_task(time_limit=180)
def execute_post_collection_bots(filter: dict | None = None):
    core_api = CoreApi()
    if bot_configs := core_api.get_post_collection_bots_config():
        return bot_tasks.execute_by_configs(bot_configs, filter)
    return "No post collection bots found"


@shared_task(time_limit=10)
def cleanup_token_blacklist():
    core_api = CoreApi()
    core_api.cleanup_token_blacklist()
    return "Token blacklist cleaned up"


@shared_task(time_limit=30)
def gather_word_list(word_list_id: int):
    core_api = CoreApi()
    if word_list := core_api.get_word_list(word_list_id):
        return bot_tasks.execute_by_type("wordlist_bot", word_list)

    logger.error(f"Word list with id {word_list_id} not found")
    return f"Word list with id {word_list_id} not found"
