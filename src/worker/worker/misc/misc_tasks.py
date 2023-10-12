from celery import shared_task

from worker.core_api import CoreApi
from worker.misc.wordlist_update import update_wordlist


@shared_task(time_limit=10, name="cleanup_token_blacklist")
def cleanup_token_blacklist():
    core_api = CoreApi()
    core_api.cleanup_token_blacklist()
    return "Token blacklist cleaned up"


@shared_task(time_limit=30, name="gather_word_list")
def gather_word_list(word_list_id: int):
    return update_wordlist(word_list_id)
