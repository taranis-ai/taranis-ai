from datetime import datetime, timezone
from typing import Any

from models.task import Task as TaskResponseModel
from models.task import TaskHistoryResponse, TaskSubmission

from core.config import Config
from core.log import logger
from core.model.product import Product
from core.model.task import Task as TaskModel
from core.model.token_blacklist import TokenBlacklist
from core.model.word_list import WordList
from core.service import cache_invalidation as cache_invalidation_module
from core.service.misp_story_sync import handle_misp_connector_result
from core.service.news_item_tag import NewsItemTagService


TAGGING_BOTS = {"WORDLIST_BOT", "IOC_BOT", "NLP_BOT", "TAGGING_BOT"}


class TaskService:
    @staticmethod
    def get_task(task_id: str) -> tuple[dict[str, Any], int]:
        if result := TaskModel.get(task_id):
            validated = TaskResponseModel.model_validate(result.to_dict())
            return validated.model_dump(mode="json", exclude_none=False), 200
        return {"status": "PENDING"}, 404

    @staticmethod
    def get_tasks(filter_args: dict[str, Any] | None = None, user: Any = None) -> tuple[dict[str, Any], int]:
        result, status = TaskModel.get_all_for_api(filter_args=filter_args, with_count=True, user=user)
        if status != 200:
            return result, status

        result.update(TaskModel.get_task_statistics())
        validated = TaskHistoryResponse.model_validate(result)
        return validated.model_dump(mode="json", exclude_none=False), status

    @staticmethod
    def delete_task(task_id: str) -> tuple[dict[str, Any], int]:
        return TaskModel.delete(task_id)

    @classmethod
    def save_task_result(cls, submission: TaskSubmission) -> tuple[dict[str, Any], int]:
        task_kind = cls._resolve_task_kind(submission.id, submission.task)
        payload: dict[str, Any] = {
            "id": submission.id,
            "result": submission.result,
            "status": submission.status,
        }
        if submission.task is not None:
            payload["task"] = submission.task
        if submission.worker_id is not None:
            payload["worker_id"] = submission.worker_id
        if submission.worker_type is not None:
            payload["worker_type"] = submission.worker_type

        result, _ = TaskModel.add_or_update(payload)
        cls._handle_task_result(
            task_kind=task_kind,
            status=submission.status,
            result=submission.result,
            worker_id=submission.worker_id,
            worker_type=submission.worker_type,
            job_id=submission.id,
        )
        validated = TaskResponseModel.model_validate(result)
        return validated.model_dump(mode="json", exclude_none=False), 200

    @staticmethod
    def _resolve_task_kind(task_id: str, task_name: str | None) -> str | None:
        task_name = task_name or ""

        if task_name == "gather_word_list" or task_id.startswith("gather_word_list"):
            return "gather_word_list"
        if task_name == "cleanup_token_blacklist" or task_id.startswith("cleanup_token_blacklist"):
            return "cleanup_token_blacklist"
        if task_name == "presenter_task" or task_id.startswith("presenter_task"):
            return "presenter_task"
        if task_name == "collector_preview" or task_id.startswith("source_preview_"):
            return "collector_preview"
        if task_name == "collector_task" or task_name.startswith("collect_") or task_id.startswith("collect_"):
            return "collector_task"
        if task_name == "bot_task" or task_name.startswith("bot_") or task_id.startswith("bot"):
            return "bot_task"
        if task_name == "connector_task":
            return "connector_task"
        if task_name == "publisher_task" or task_id.startswith("publisher_task"):
            return "publisher_task"

        return None

    @classmethod
    def _handle_task_result(
        cls,
        *,
        task_kind: str | None,
        status: str,
        result: dict[str, Any],
        worker_id: str | None,
        worker_type: str | None,
        job_id: str,
    ) -> None:
        if task_kind == "collector_task" and status not in TaskModel.SUCCESS_STATUSES:
            cache_invalidation_module.cache_invalidation_service.invalidate_model("admin_menu_badges")
            cache_invalidation_module.cache_invalidation_service.invalidate_model("osint_source", worker_id)
            return

        if status not in TaskModel.SUCCESS_STATUSES or not task_kind:
            return

        cache_invalidation_module.invalidate_frontend_cache_on_success(200, full=True)
        handler = cls._SUCCESS_RESULT_HANDLERS.get(task_kind)
        if handler is not None:
            handler(cls, result=result, worker_id=worker_id, worker_type=worker_type, job_id=job_id)

    @classmethod
    def _handle_cleanup_result(cls, *, result: dict[str, Any], **_: Any) -> None:
        del result
        check_time = datetime.now(timezone.utc).replace(tzinfo=None) - Config.JWT_ACCESS_TOKEN_EXPIRES
        TokenBlacklist.delete_older(check_time)

    @classmethod
    def _handle_collector_result(cls, *, result: dict[str, Any], worker_id: str | None, job_id: str, **_: Any) -> None:
        logger.info("Collector task %s completed with result: %s", job_id, result)
        cache_invalidation_module.cache_invalidation_service.invalidate_model("osint_source", worker_id)

    @classmethod
    def _handle_connector_result(cls, *, result: dict[str, Any], **_: Any) -> None:
        handle_misp_connector_result(result)

    @classmethod
    def _handle_word_list_result(cls, *, result: dict[str, Any], **_: Any) -> None:
        WordList.update_word_list(
            word_list_id=result["word_list_id"],
            content=result["content"],
            content_type=result["content_type"],
        )

    @classmethod
    def _handle_presenter_result(cls, *, result: dict[str, Any], **_: Any) -> None:
        product_id = result.get("product_id")
        rendered_product = result.get("render_result")

        if not isinstance(product_id, str) or not isinstance(rendered_product, str):
            logger.error(f"Product {product_id} not found or no render result")
            return

        Product.update_render_for_id(product_id, rendered_product)

    @classmethod
    def _handle_bot_result(
        cls,
        *,
        result: dict[str, Any],
        worker_id: str | None,
        worker_type: str | None,
        **_: Any,
    ) -> None:
        worker_type = worker_type or ""
        worker_id = worker_id or "UNKNOWN_ID"
        bot_result = {
            key: value for key, value in result.items() if key not in {"bot_id", "message", "tagged_items", "tags_applied", "news_items"}
        }

        if worker_type in TAGGING_BOTS:
            NewsItemTagService.set_found_bot_tags(bot_result, actor="bot")

        NewsItemTagService.set_worker_execution_attribute(worker_type=worker_type, worker_id=worker_id, found_tags=bot_result)

    _SUCCESS_RESULT_HANDLERS = {
        "cleanup_token_blacklist": _handle_cleanup_result.__func__,
        "collector_task": _handle_collector_result.__func__,
        "connector_task": _handle_connector_result.__func__,
        "gather_word_list": _handle_word_list_result.__func__,
        "presenter_task": _handle_presenter_result.__func__,
        "bot_task": _handle_bot_result.__func__,
    }
