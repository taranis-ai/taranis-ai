"""RQ Bot Tasks

Functions for executing bots to process news items.
"""

from typing import Any

from models.worker_parameters import effective_parameter_values
from rq import get_current_job

import worker.bots
from worker.bot_api import BotServiceUnavailableError
from worker.core_api import CoreApi, build_failure_task_result, build_success_task_result
from worker.http_client import http_session_scope
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
        bot_config = core_api.get_bot_config(bot_id)
        if not bot_config:
            raise ValueError(f"Bot with id {bot_id} not found")

        worker_type = bot_config.get("type", worker_type).upper()
        bot = _bot_for_config(bot_config)
        bot_result = _execute_by_config(bot_config, filter, bot=bot)
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
                    "bot_stages": [_stage(bot_id, worker_type, bot_result)],
                    "story_revisions": getattr(bot, "story_revisions", {}),
                },
                merge_dict_data=False,
            ),
        )
        if not saved:
            raise RuntimeError("Bot result could not be submitted")
        return (
            {"worker_id": bot_id, "worker_type": worker_type, **bot_result}
            if isinstance(bot_result, dict)
            else {"worker_id": bot_id, "worker_type": worker_type, "result": bot_result}
        )
    except Exception as exc:
        not_found = isinstance(exc, ValueError) and exc.args == (f"Bot with id {bot_id} not found",)
        empty_result = isinstance(exc, RuntimeError) and exc.args == (f"Bot {bot_id} returned no result",)
        if isinstance(exc, BotServiceUnavailableError):
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
        if isinstance(exc, BotServiceUnavailableError):
            raise
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


def _execute_by_config(bot_config: dict, filter: dict | None = None, *, bot=None):
    bot = bot or _bot_for_config(bot_config)
    bot_type = bot_config["type"]
    bot_params: dict[str, Any] = effective_parameter_values(bot_type, bot_config.get("parameters", {}))

    if filter:
        # Runtime filters are transient task data, not persisted parameters.
        bot_params["filter"] = filter

    return bot.execute(bot_params)


def _stage(bot_id: str, bot_type: str, result: dict) -> dict:
    return {"bot_id": bot_id, "bot_type": bot_type, "result": result}


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
        configs = []
        bots = []
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
            bots.append(bot)

        snapshot = core_api.get_pipeline_stories(filters)
        if snapshot is None:
            raise RuntimeError("Bot stories could not be loaded")
        stories = {story["id"]: story for story in snapshot["stories"]}
        aliases: dict[str, str] = {}
        stages = []
        for config, bot in zip(configs, bots, strict=True):
            bot_id = config["id"]
            selected = snapshot["selected"][bot_id]
            selected_ids = list(dict.fromkeys(aliases.get(story_id, story_id) for story_id in selected))
            bot.pipeline_stories = [stories[story_id] for story_id in selected_ids if story_id in stories]
            result = _execute_by_config(config, filter, bot=bot)
            if result is None:
                raise RuntimeError("Bot returned no result")
            bot_type = config["type"].upper()
            stages.append(_stage(bot_id, bot_type, result))
            _apply_context(stories, aliases, bot_type, result)

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
        return {"worker_type": "BOT_PIPELINE", "bots": bot_ids, "stories": len(snapshot["stories"])}
    except Exception as exc:
        is_unavailable = isinstance(exc, BotServiceUnavailableError)
        core_api.save_task_result(
            run_id,
            "bot_pipeline",
            "FAILURE",
            worker_type="BOT_PIPELINE",
            result=build_failure_task_result(
                exc.public_message if is_unavailable else "Bot pipeline failed",
                reason=exc.reason if is_unavailable else "bot_pipeline_failed",
                retryable=exc.retryable if is_unavailable else False,
                data={"bot_ids": bot_ids, "filter": filter},
            ),
        )
        raise
