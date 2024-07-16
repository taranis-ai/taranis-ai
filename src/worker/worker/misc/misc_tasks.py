from celery import shared_task

from worker.misc.wordlist_update import update_wordlist


@shared_task(time_limit=10, name="cleanup_token_blacklist", ignore_result=True, priority=1)
def cleanup_token_blacklist(*args, **kwargs):
    return "Trigger blacklist cleaneup"


@shared_task(time_limit=120, name="gather_word_list", priority=1)
def gather_word_list(word_list_id: int):
    return update_wordlist(word_list_id)
