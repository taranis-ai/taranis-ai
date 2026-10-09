"""RQ Bot Tasks

Functions for executing bots to process news items.
"""

from typing import Any

from models.llm import LLM_BOT_FEATURES
from models.worker_parameters import effective_parameter_values
from rq import Retry, get_current_job

import worker.bots
from worker.bot_api import BotServiceUnavailableError
from worker.core_api import CoreApi, build_failure_task_result, build_success_task_result
from worker.http_client import http_session_scope
from worker.llm import LLMConfigurationError
from worker.llm_batch import BatchExecutionError
from worker.log import logger
from worker.telemetry import instrument_job


TAGGING_BOTS = {"WORDLIST_BOT", "IOC_BOT", "NLP_BOT", "TAGGING_BOT"}


@instrument_job
@http_session_scope()
def bot_task(bot_id: str, filter: dict | None = None, trigger_dependents: bool = True):
    """Execute a bot to process news items.

    Args:
        bot_id: ID of the bot to execute
        filter: Optional filter to limit which items the bot processes

    Returns:
        Result from the bot execution

    Raises:
        ValueError: If bot not found or misconfigured
    """
    job = get_current_job()
    core_api = CoreApi()
    task_name = f"bot_{bot_id}"
    task_id = job.id if job else task_name
    worker_type = "BOT_TASK"

    logger.info(f"Starting bot task with job id {job.id if job else 'manual'}")

    try:
        batch_state = job.meta.get("llm_batch") if job and isinstance(job.meta, dict) else None
        bot_config = batch_state["config"] if batch_state else core_api.get_bot_config(bot_id)
        if not bot_config:
            raise ValueError(f"Bot with id {bot_id} not found")

        worker_type = bot_config.get("type", worker_type).upper()
        if (bot_config.get("llm_endpoint") or {}).get("processing_mode") == "openrouter_batch":
            if not job:
                raise RuntimeError("Batch processing requires a queued job")
            if batch_state is None:
                batch_state = {"config": bot_config}
                job.meta["llm_batch"] = batch_state
                job.save_meta()
        bot = _bot_for_config(bot_config)
        bot_result = _execute_by_config(bot_config, filter, bot=bot, batch_state=batch_state, save_batch_state=job.save_meta if job else None)
        if isinstance(bot_result, Retry):
            return bot_result
        if bot_result is None:
            raise RuntimeError(f"Bot {bot_id} returned no result")
        saved = core_api.save_task_result(
            task_id,
            task_name,
            "SUCCESS",
            worker_id=bot_id,
            worker_type=worker_type,
            result=build_success_task_result(
                default_message=f"Bot {bot_id} executed successfully",
                output=bot_result,
                base_data={
                    "bot_id": bot_id,
                    "filter": filter,
                    "trigger_dependents": trigger_dependents,
                    "bot_stages": [_stage(bot_id, worker_type, bot_result, list(getattr(bot, "story_revisions", {})))],
                    "story_revisions": getattr(bot, "story_revisions", {}),
                },
                merge_dict_data=False,
            ),
        )
        if not saved:
            raise RuntimeError("Bot result could not be submitted")
        if batch_state is not None:
            assert job is not None
            job.meta.pop("llm_batch", None)
            job.save_meta()
        return (
            {"worker_id": bot_id, "worker_type": worker_type, **bot_result}
            if isinstance(bot_result, dict)
            else {"worker_id": bot_id, "worker_type": worker_type, "result": bot_result}
        )
    except Exception as exc:
        not_found = isinstance(exc, ValueError) and exc.args == (f"Bot with id {bot_id} not found",)
        empty_result = isinstance(exc, RuntimeError) and exc.args == (f"Bot {bot_id} returned no result",)
        if isinstance(exc, (BotServiceUnavailableError, LLMConfigurationError, BatchExecutionError)):
            error_message = exc.public_message
            reason = exc.reason
            retryable = exc.retryable
        elif not_found:
            error_message = f"Bot with id {bot_id} not found"
            reason = "bot_not_found"
            retryable = False
        elif empty_result:
            error_message = f"Bot {bot_id} returned no result"
            reason = "bot_empty_result"
            retryable = False
        else:
            error_message = "Bot execution failed"
            reason = "bot_execution_failed"
            retryable = False
        core_api.save_task_result(
            task_id,
            task_name,
            "FAILURE",
            worker_id=bot_id,
            worker_type=worker_type,
            result=build_failure_task_result(
                error_message,
                reason=reason,
                retryable=retryable,
                data={"bot_id": bot_id, "filter": filter, "trigger_dependents": trigger_dependents},
            ),
        )
        raise


def _bot_for_config(bot_config: dict):
    """Create the configured bot."""
    bot_type = bot_config.get("type")
    if not bot_type:
        raise ValueError("Bot has no type")
    bots = {
        "analyst_bot": worker.bots.AnalystBot,
        "grouping_bot": worker.bots.GroupingBot,
        "tagging_bot": worker.bots.TaggingBot,
        "wordlist_bot": worker.bots.WordlistBot,
        "nlp_bot": worker.bots.NLPBot,
        "story_bot": worker.bots.StoryBot,
        "ioc_bot": worker.bots.IOCBot,
        "intel_owl_bot": worker.bots.IntelOwlBot,
        "summary_bot": worker.bots.SummaryBot,
        "sentiment_analysis_bot": worker.bots.SentimentAnalysisBot,
        "cybersec_classifier_bot": worker.bots.CyberSecClassifierBot,
    }

    bot_class = bots.get(bot_type)
    if not bot_class:
        raise ValueError(f"Bot type '{bot_type}' not implemented")
    return bot_class()


def _execute_by_config(bot_config: dict, filter: dict | None = None, *, bot=None, batch_state: dict | None = None, save_batch_state=None):
    bot = bot or _bot_for_config(bot_config)
    bot_type = bot_config["type"]
    bot_params: dict[str, Any] = effective_parameter_values(bot_type, bot_config.get("parameters", {}))

    if bot_type in LLM_BOT_FEATURES:
        bot_params["llm_endpoint"] = bot_config.get("llm_endpoint")

    if filter:
        # Runtime filters are transient task data, not persisted parameters.
        bot_params["filter"] = filter

    if batch_state is not None:
        if "stories" not in batch_state:
            batch_state["stories"] = bot.get_stories(dict(bot_params))
        bot_params["_stories"] = batch_state["stories"]
        bot_params["_llm_batch_state"] = batch_state
        bot_params["_save_llm_batch_state"] = save_batch_state

    return bot.execute(bot_params)


def _stage(bot_id: str, bot_type: str, result: dict, story_ids: list[str]) -> dict:
    return {"bot_id": bot_id, "bot_type": bot_type, "story_ids": story_ids, "result": result}


def _apply_context(stories: dict[str, dict], aliases: dict[str, str], bot_type: str, result: dict) -> None:
    changes = result.get("changes") or {}
    items = {item["id"]: item for story in stories.values() for item in story.get("news_items", [])}
    if bot_type in TAGGING_BOTS:
        for item_id, tags in result.items():
            if item := items.get(item_id):
                existing = item.setdefault("tags", [])
                if isinstance(existing, dict):
                    existing = list(existing.values())
                    item["tags"] = existing
                names = {tag.get("name") for tag in existing if isinstance(tag, dict)}
                incoming = (
                    ((name, value.get("tag_type", "misc") if isinstance(value, dict) else value) for name, value in tags.items())
                    if isinstance(tags, dict)
                    else ((tag.get("name"), tag.get("tag_type", "misc")) if isinstance(tag, dict) else (tag, "misc") for tag in tags)
                )
                for name, tag_type in incoming:
                    if isinstance(name, str) and name not in names:
                        existing.append({"name": name, "tag_type": tag_type})
                        names.add(name)
        for story in stories.values():
            story["tags"] = {
                tag["name"]: tag
                for item in story.get("news_items", [])
                for tag in item.get("tags", [])
                if isinstance(tag, dict) and isinstance(tag.get("name"), str)
            }
    for item_id, attributes in changes.get("item_attributes", {}).items():
        if item := items.get(item_id):
            existing = item.setdefault("attributes", [])
            if isinstance(existing, list):
                existing = {attribute["key"]: attribute for attribute in existing}
            for attribute in attributes:
                existing[attribute["key"]] = attribute
            item["attributes"] = list(existing.values())
    for story_id, attributes in changes.get("story_attributes", {}).items():
        if story := stories.get(aliases.get(story_id, story_id)):
            existing = story.setdefault("attributes", {})
            for attribute in attributes:
                existing[attribute["key"]] = attribute
    for story_id, updates in changes.get("story_updates", {}).items():
        if story := stories.get(aliases.get(story_id, story_id)):
            story.update(updates)
    for group in changes.get("groups", []):
        resolved = list(dict.fromkeys(aliases.get(story_id, story_id) for story_id in group))
        if len(resolved) < 2 or resolved[0] not in stories:
            continue
        target = stories[resolved[0]]
        for source_id in resolved[1:]:
            if source := stories.pop(source_id, None):
                target["news_items"].extend(source.get("news_items", []))
                aliases[source_id] = resolved[0]
        for old_id, current_id in list(aliases.items()):
            if current_id in resolved[1:]:
                aliases[old_id] = resolved[0]


@instrument_job
@http_session_scope()
def bot_pipeline_task(bot_ids: list[str], filter: dict | None = None):
    """Run a configured DAG with one story snapshot and one successful submission."""
    job = get_current_job()
    run_id = job.id if job else "bot_pipeline"
    core_api = CoreApi()
    try:
        state: dict[str, Any] | None = job.meta.get("bot_pipeline") if job and isinstance(job.meta, dict) else None
        if state is None:
            configs = []
            filters = {}
            for bot_id in bot_ids:
                config = core_api.get_bot_config(bot_id)
                if not config:
                    raise ValueError("Bot configuration is unavailable")
                bot = _bot_for_config(config)
                params = effective_parameter_values(config["type"], config.get("parameters", {}))
                if filter:
                    params["filter"] = filter
                filters[bot_id] = bot.get_filter_dict(dict(params))
                configs.append(config)

            uses_batch = any((config.get("llm_endpoint") or {}).get("processing_mode") == "openrouter_batch" for config in configs)
            if uses_batch and not job:
                raise RuntimeError("Batch processing requires a queued job")
            snapshot = core_api.get_pipeline_stories(filters)
            if snapshot is None:
                raise RuntimeError("Bot stories could not be loaded")
            state = {
                "configs": configs,
                "snapshot": snapshot,
                "stories": {story["id"]: story for story in snapshot["stories"]},
                "aliases": {},
                "stages": [],
                "llm_batch": {},
            }
            if uses_batch:
                assert job is not None
                job.meta["bot_pipeline"] = state
                job.save_meta()

        snapshot = state["snapshot"]
        stories = state["stories"]
        aliases = state["aliases"]
        stages = state["stages"]
        for config in state["configs"][len(stages) :]:
            bot = _bot_for_config(config)
            bot_id = config["id"]
            selected = snapshot["selected"][bot_id]
            selected_ids = list(dict.fromkeys(aliases.get(story_id, story_id) for story_id in selected))
            bot.pipeline_stories = [stories[story_id] for story_id in selected_ids if story_id in stories]
            batch_state = state["llm_batch"] if (config.get("llm_endpoint") or {}).get("processing_mode") == "openrouter_batch" else None
            result = _execute_by_config(config, filter, bot=bot, batch_state=batch_state, save_batch_state=job.save_meta if job else None)
            if isinstance(result, Retry):
                return result
            if result is None:
                raise RuntimeError("Bot returned no result")
            bot_type = config["type"].upper()
            stages.append(_stage(bot_id, bot_type, result, [story["id"] for story in bot.pipeline_stories]))
            _apply_context(stories, aliases, bot_type, result)
            state["llm_batch"] = {}
            if job and "bot_pipeline" in job.meta:
                job.save_meta()

        saved = core_api.save_task_result(
            run_id,
            "bot_pipeline",
            "SUCCESS",
            worker_type="BOT_PIPELINE",
            result=build_success_task_result(
                default_message=f"Ran {len(stages)} bots",
                data={
                    "bot_stages": stages,
                    "story_revisions": snapshot["revisions"],
                    "filter": filter,
                    "trigger_dependents": False,
                },
            ),
        )
        if not saved:
            raise RuntimeError("Bot pipeline result could not be submitted")
        if job and "bot_pipeline" in job.meta:
            job.meta.pop("bot_pipeline")
            job.save_meta()
        return {"worker_type": "BOT_PIPELINE", "bots": bot_ids, "stories": len(snapshot["stories"])}
    except Exception as exc:
        logger.exception("Bot pipeline failed")
        is_public = isinstance(exc, (BotServiceUnavailableError, LLMConfigurationError, BatchExecutionError))
        core_api.save_task_result(
            run_id,
            "bot_pipeline",
            "FAILURE",
            worker_type="BOT_PIPELINE",
            result=build_failure_task_result(
                exc.public_message if is_public else "Bot pipeline failed",
                reason=exc.reason if is_public else "bot_pipeline_failed",
                retryable=exc.retryable if is_public else False,
                data={"bot_ids": bot_ids, "filter": filter},
            ),
        )
        raise
