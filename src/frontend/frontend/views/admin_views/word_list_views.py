import json
from typing import Any

from flask import Response, render_template, request
from models.admin import WordList

from frontend.auth import admin_required
from frontend.config import Config
from frontend.core_api import CoreApi
from frontend.data_persistence import DataPersistenceLayer
from frontend.filters import render_count
from frontend.log import logger
from frontend.views.admin_views.admin_base_view import AdminBaseView


class WordListView(AdminBaseView):
    model = WordList
    icon = "chat-bubble-bottom-center-text"
    _index = 170

    @classmethod
    def import_view(cls, error=None):
        return render_template(f"{cls.model_name().lower()}/{cls.model_name().lower()}_import.html", error=error)

    @classmethod
    def import_post_view(cls):
        word_lists = request.files.get("file")
        if not word_lists:
            return cls.render_form_error("No file provided")
        data = word_lists.read()
        try:
            data = json.loads(data)
        except ValueError as exc:
            return cls.render_form_error(str(exc))

        response = CoreApi().import_word_lists(data)

        if not response or not response.ok:
            return cls.render_form_error(cls.get_response_error_message(response, "Failed to import word lists"))

        return Response(status=200, headers={"HX-Refresh": "true"})

    @classmethod
    @admin_required()
    def export_view(cls):
        word_list_ids = request.args.getlist("ids")
        core_resp = CoreApi().export_word_lists({"ids": word_list_ids})

        if not core_resp:
            logger.warning(f"Failed to fetch word lists from: {Config.TARANIS_CORE_URL}")
            return f"Failed to fetch word lists from: {Config.TARANIS_CORE_URL}", 500

        return CoreApi.stream_proxy(core_resp, "word_lists_export.json")

    @classmethod
    @admin_required()
    def load_default_word_lists(cls):
        dpl = DataPersistenceLayer()
        response = CoreApi().load_default_word_lists()
        if not response:
            logger.error("Failed to load default word lists")
            return render_template("notification/index.html", notification={"message": "Failed to load default word lists", "error": True})

        core_response = CoreApi().import_word_lists(response)

        if not core_response.ok:
            error = cls.get_response_error_message(core_response, "Unknown error")
            error_message = f"Failed to import default word lists: {error}"
            logger.error(error_message)
            return render_template(
                "notification/index.html", notification={"message": error_message, "error": True}
            ), core_response.status_code

        dpl.invalidate_cache_by_object(cls.model)
        dpl.invalidate_model_cache_locally(cls.model)
        items = dpl.get_objects(cls.model)
        return render_template(cls.get_list_template(), **cls.get_view_context(items)), core_response.status_code

    @classmethod
    @admin_required()
    def update_word_lists(cls, word_list_id: str | None = None):
        dpl = DataPersistenceLayer()
        core_response = CoreApi().update_word_lists(word_list_id)
        if not core_response.ok:
            response = cls.get_notification_from_response(core_response)
            return response, core_response.status_code

        response = cls.get_notification_from_response(core_response)

        dpl.invalidate_cache_by_object(cls.model)
        dpl.invalidate_model_cache_locally(cls.model)

        table, table_response = cls.render_list()
        if table_response == 200:
            response += table
        return response, core_response.status_code

    @classmethod
    def get_columns(cls) -> list[dict[str, Any]]:
        return [
            {"title": "Name", "field": "name", "sortable": True, "renderer": None},
            {"title": "Description", "field": "description", "sortable": True, "renderer": None},
            {
                "title": "Words",
                "field": "entries",
                "sortable": False,
                "renderer": render_count,
                "render_args": {"field": "entries"},
            },
        ]
