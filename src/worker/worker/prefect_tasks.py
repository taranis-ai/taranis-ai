from prefect import flow

from worker.core_api import CoreApi
from worker.misc.wordlist_update import update_wordlist


@flow(name="cleanup_token_blacklist", timeout_seconds=10)
def cleanup_token_blacklist():
    core_api = CoreApi()
    core_api.cleanup_token_blacklist()
    return "Token blacklist cleaned up"


@flow(name="gather_word_list", timeout_seconds=120, flow_run_name="gather_word_list-{word_list_id}")
def gather_word_list(word_list_id: int):
    return update_wordlist(word_list_id)


flow.register(project_name="taranis-ai-misc")
