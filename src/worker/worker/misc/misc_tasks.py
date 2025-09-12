from worker.misc.wordlist_update import update_wordlist
from prefect import flow, task
from worker.log import logger


@flow(name="cleanup_token_blacklist")
def cleanup_token_blacklist(*args, **kwargs):
    return "Trigger blacklist cleaneup"


@flow(name="gather_word_list")
def gather_word_list(word_list_id: int):
    return update_wordlist(word_list_id)


@flow(log_prints=True, flow_run_name="debug_flow")
async def debug_flow(names: list[str]) -> None:
    for name in names:
        await debug_task(name=name)


@task(task_run_name="debug_task", log_prints=True)
async def debug_task(name: str) -> None:
    logger.debug(f"Debug task executed: {name}")
