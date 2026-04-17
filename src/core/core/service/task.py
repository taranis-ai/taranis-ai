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
from core.service.cache_invalidation import invalidate_frontend_cache_on_success
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

        result.update(TaskModel.get_task_statistics(group_by_worker_type=True))
        validated = TaskHistoryResponse.model_validate(result)
        return validated.model_dump(mode="json", exclude_none=False), status

    @staticmethod
    def delete_task(task_id: str) -> tuple[dict[str, Any], int]:
        return TaskModel.delete(task_id)

    @classmethod
    def save_task_result(cls, submission: TaskSubmission) -> tuple[dict[str, Any], int]:
        if submission.status == "SUCCESS" and submission.result is not None:
            cls._handle_success_result(submission)

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
        if task_name == "collector_task" or task_name.startswith("collect_") or task_id.startswith("collect_"):
            return "collector_task"
        if task_name == "bot_task" or task_name.startswith("bot_") or task_id.startswith("bot"):
            return "bot_task"
        if task_name == "connector_task":
            return "connector_task"

        return None

    @classmethod
    def _handle_success_result(cls, submission: TaskSubmission) -> None:
        invalidate_frontend_cache_on_success(200, full=True)
        task_kind = cls._resolve_task_kind(submission.id, submission.task)
        if not task_kind:
            return

        if task_kind == "cleanup_token_blacklist":
            check_time = datetime.now(timezone.utc).replace(tzinfo=None) - Config.JWT_ACCESS_TOKEN_EXPIRES
            TokenBlacklist.delete_older(check_time)
            return

        if task_kind == "collector_task":
            logger.info(f"Collector task {submission.id} completed with result: {submission.result}")
            return

        if task_kind == "connector_task":
            handle_misp_connector_result(submission.result)  # type: ignore TODO: validate result before handling
            return

        if not isinstance(submission.result, dict):
            logger.error(f"Invalid {task_kind} result type: {type(submission.result)}. Expected dict.")
            return

        if task_kind == "gather_word_list":
            WordList.update_word_list(**submission.result)
            return

        if task_kind == "presenter_task":
            cls._handle_presenter_result(submission.result)
            return

        if task_kind == "bot_task":
            cls._handle_bot_result(submission)

    @staticmethod
    def _handle_presenter_result(result: dict[str, Any]) -> None:
        product_id = result.get("product_id")
        rendered_product = result.get("render_result")

        if not isinstance(product_id, str) or not isinstance(rendered_product, str):
            logger.error(f"Product {product_id} not found or no render result")
            return

        Product.update_render_for_id(product_id, rendered_product)

    @staticmethod
    def _handle_bot_result(submission: TaskSubmission) -> None:
        worker_type = submission.worker_type or ""
        worker_id = submission.worker_id or "UNKNOWN_ID"
        bot_result = submission.result
        if not isinstance(bot_result, dict):
            logger.error("Invalid bot task result payload")
            return

        if worker_type in TAGGING_BOTS:
            NewsItemTagService.set_found_bot_tags(bot_result, change_by_bot=True)

        NewsItemTagService.set_worker_execution_attribute(worker_type=worker_type, worker_id=worker_id, found_tags=bot_result)
